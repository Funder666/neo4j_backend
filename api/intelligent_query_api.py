# -*- coding: utf-8 -*-
"""
智能查询API模块

本模块提供两个核心API接口：
1. 自然语言转Cypher查询接口 - 将用户的自然语言描述转换为Neo4j Cypher查询语句
2. Cypher查询执行接口 - 执行Cypher查询语句并返回JSON格式的查询结果

主要功能：
- 基于阿里云DashScope API的自然语言处理
- 动态获取知识图谱Schema信息
- 安全的Cypher查询执行和结果格式化
- 完整的错误处理和日志记录

技术特性：
- 使用qwen3-coder-plus模型进行查询生成
- 自动清理AI返回的markdown格式代码
- 支持复杂查询的参数化处理
- 提供详细的API响应和错误信息

运行方式：
    python intelligent_query_api.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import logging
import json
import time
import re
import httpx
from datetime import datetime
import uvicorn
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j连接配置
NEO4J_URI = "bolt://8.153.207.172:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "xtxzhu2u"

# 全局Neo4j驱动
neo4j_driver = None

# 阿里云DashScope API配置
DASHSCOPE_API_KEY = "sk-f55b7b2a02a4478fbdcb48c30d90bb49"
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 创建FastAPI应用
app = FastAPI(
    title="智能查询API",
    description="Neo4j图数据库智能查询服务",
    version="1.0.0"
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_neo4j():
    """初始化Neo4j连接"""
    global neo4j_driver
    try:
        neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        # 测试连接
        with neo4j_driver.session() as session:
            result = session.run("RETURN 1")
            result.single()
        logger.info("Neo4j连接初始化成功")
    except Exception as e:
        logger.error(f"Neo4j连接初始化失败: {e}")
        raise

def close_neo4j():
    """关闭Neo4j连接"""
    global neo4j_driver
    if neo4j_driver:
        neo4j_driver.close()
        logger.info("Neo4j连接已关闭")

def record_to_dict(record):
    """将Neo4j记录转换为字典格式"""
    result = {}
    for key in record.keys():
        value = record[key]
        if isinstance(value, Node):  # 节点对象
            result[key] = dict(value)
            result[key]['id'] = value.id
            result[key]['labels'] = list(value.labels)
        elif isinstance(value, Relationship):  # 关系对象
            result[key] = dict(value)
            result[key]['id'] = value.id
            result[key]['type'] = value.type
            result[key]['start_node_id'] = value.start_node.id if hasattr(value, 'start_node') else None
            result[key]['end_node_id'] = value.end_node.id if hasattr(value, 'end_node') else None
        else:
            result[key] = value
    return result

def convert_neo4j_integers(params):
    """转换参数中的整数为Neo4j兼容格式"""
    if isinstance(params, dict):
        return {k: v for k, v in params.items()}
    return params

# Pydantic模型定义
class NaturalLanguageQueryRequest(BaseModel):
    """自然语言查询请求模型"""
    query: str = Field(..., description="自然语言查询语句", min_length=1, max_length=500)
    include_schema: bool = Field(default=True, description="是否在AI提示中包含完整的Schema信息")
    temperature: float = Field(default=0.1, description="AI模型的创造性参数", ge=0.0, le=1.0)
    max_tokens: int = Field(default=500, description="AI响应的最大token数", ge=50, le=2000)

class CypherQueryRequest(BaseModel):
    """Cypher查询请求模型"""
    cypher: str = Field(..., description="Cypher查询语句", min_length=1, max_length=2000)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="查询参数")
    limit: Optional[int] = Field(default=None, description="结果数量限制")

class NaturalLanguageQueryResponse(BaseModel):
    """自然语言查询响应模型"""
    success: bool = Field(description="操作是否成功")
    cypher_query: str = Field(description="生成的Cypher查询语句")
    generation_time_ms: int = Field(description="查询生成耗时（毫秒）")
    schema_used: bool = Field(description="是否使用了Schema信息")
    message: str = Field(default="", description="附加信息或错误消息")

class CypherQueryResponse(BaseModel):
    """Cypher查询响应模型"""
    success: bool = Field(description="操作是否成功")
    records: List[Dict[str, Any]] = Field(description="查询结果记录")
    count: int = Field(description="结果数量")
    execution_time_ms: int = Field(description="查询执行耗时（毫秒）")
    cypher_query: str = Field(description="执行的Cypher查询语句")
    message: str = Field(default="", description="附加信息或错误消息")

async def get_knowledge_graph_schema() -> Dict[str, Any]:
    """
    获取知识图谱的Schema信息

    返回包含节点类型和关系类型信息的字典，用于AI生成准确的Cypher查询

    Returns:
        Dict[str, Any]: 包含node_types和relationship_types的Schema信息

    Raises:
        Exception: 当获取Schema信息失败时
    """
    try:
        with neo4j_driver.session() as session:
            # 获取节点标签信息
            labels_query = """
            CALL db.labels() YIELD label
            WITH label
            MATCH (n) WHERE label IN labels(n)
            RETURN label, count(n) as count
            ORDER BY count DESC
            """
            labels_result = session.run(labels_query)

            # 获取关系类型信息
            relationships_query = """
            CALL db.relationshipTypes() YIELD relationshipType
            WITH relationshipType
            MATCH ()-[r]->() WHERE type(r) = relationshipType
            RETURN relationshipType, count(r) as count
            ORDER BY count DESC
            """
            relationships_result = session.run(relationships_query)

            # 处理节点类型数据
            node_types = []
            for record in labels_result:
                node_types.append({
                    "neo4j_name": record["label"],
                    "count": record["count"]
                })

            # 处理关系类型数据
            relationship_types = []
            for record in relationships_result:
                relationship_types.append({
                    "neo4j_name": record["relationshipType"],
                    "count": record["count"]
                })

            return {
                "node_types": node_types,
                "relationship_types": relationship_types,
                "generated_at": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"获取Schema信息失败: {e}")
        raise Exception(f"获取Schema信息失败: {str(e)}")

def build_ai_system_prompt(schema: Dict[str, Any]) -> str:
    """
    构建AI系统提示词

    Args:
        schema (Dict[str, Any]): 知识图谱Schema信息

    Returns:
        str: 完整的AI系统提示词
    """
    system_prompt = f"""你是一个Neo4j Cypher查询专家。根据用户的自然语言问题，生成准确的Cypher查询语句。

知识图谱Schema信息：
{json.dumps(schema, ensure_ascii=False, indent=2)}

重要规则：
1. 只返回纯净的Cypher查询语句，不要包含任何解释或markdown格式
2. 查询结果数量默认不作限制，除非用户明确要求
3. 理解用户的中文描述但必须使用neo4j_name生成查询（如：用户说"汉字"要理解为Character标签）
4. 对于模糊匹配，使用CONTAINS或正则表达式
5. 确保查询语法正确且能在Neo4j中执行
6. 优先使用有方向的关系匹配，除非需要双向查询

数据类型注意事项：
- HSK等级、新标准等级、笔画数等数字字段在Neo4j中存储为字符串，请使用字符串比较
- 所有等级和数字字段都需要用引号包围，如: n.hskLevel = '1', n.strokes = '5'
- 对于范围查询，可以使用字符串比较或转换: toInteger(n.strokes) < 5

正确示例：
用户问题："查找所有HSK等级为1的汉字"
理解：用户说的"汉字"对应Character标签
Cypher: MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n

用户问题："找到笔画数少于5的汉字"
理解：查询Character标签，使用数字比较
Cypher: MATCH (n:Character) WHERE toInteger(n.strokes) < 5 RETURN n

用户问题："查找'喜爱'词汇的近义词关系"
理解：近义词关系对应NEAR_SYNONYMOUS_WITH
Cypher: MATCH (n:Word {{name: '喜爱'}})-[r:NEAR_SYNONYMOUS_WITH]-(m) RETURN n, r, m

用户问题："国际中文教育中文水平1级的词语"
理解：国际中文教育等级通过关系连接，等级节点的value为1
Cypher: MATCH (n:Word)-[r:FROM_LEVEL]->(l:InternationalLevel {{value: '1'}}) RETURN n, r, l limit 100"""

    return system_prompt

def clean_ai_generated_cypher(raw_cypher: str) -> str:
    """
    清理AI生成的Cypher查询语句

    移除可能包含的markdown格式、解释文本等，提取纯净的Cypher语句

    Args:
        raw_cypher (str): AI生成的原始文本

    Returns:
        str: 清理后的纯净Cypher查询语句
    """
    # 移除markdown代码块格式
    cypher_match = re.search(r'```(?:cypher)?\n?(.*?)\n?```', raw_cypher, re.DOTALL)
    if cypher_match:
        return cypher_match.group(1).strip()

    # 如果没有代码块，查找以MATCH、CREATE、DELETE等开头的行
    lines = raw_cypher.split('\n')
    cypher_keywords = ['MATCH', 'CREATE', 'DELETE', 'MERGE', 'RETURN', 'WITH', 'CALL']

    for line in lines:
        line = line.strip()
        if any(line.upper().startswith(keyword) for keyword in cypher_keywords):
            # 找到第一个Cypher语句，提取完整查询
            cypher_lines = [line]
            line_idx = lines.index(line)

            # 继续读取后续行，直到遇到空行或非Cypher内容
            for i in range(line_idx + 1, len(lines)):
                next_line = lines[i].strip()
                if not next_line:
                    break
                if any(next_line.upper().startswith(kw) for kw in cypher_keywords) or \
                   next_line.upper().startswith(('WHERE', 'ORDER BY', 'LIMIT', 'SKIP', 'AND', 'OR')):
                    cypher_lines.append(next_line)
                else:
                    break

            return ' '.join(cypher_lines)

    # 如果都没找到，返回原始文本的第一行
    return raw_cypher.split('\n')[0].strip()

@app.post("/out/api/intelligent/nl-to-cypher", response_model=NaturalLanguageQueryResponse)
async def natural_language_to_cypher(request: NaturalLanguageQueryRequest):
    """
    自然语言转Cypher查询接口

    将用户输入的自然语言描述转换为Neo4j Cypher查询语句。
    使用阿里云DashScope API的大语言模型进行智能转换。

    Args:
        request (NaturalLanguageQueryRequest): 包含自然语言查询和配置参数

    Returns:
        NaturalLanguageQueryResponse: 包含生成的Cypher查询和相关信息

    Raises:
        HTTPException: 当查询生成失败时返回500错误

    示例:
        请求: {"query": "查找所有HSK等级为1的汉字"}
        响应: {"success": true, "cypher_query": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n", ...}
    """
    start_time = time.time()

    try:
        # 获取知识图谱Schema（如果需要）
        schema = {}
        if request.include_schema:
            try:
                schema = await get_knowledge_graph_schema()
            except Exception as e:
                logger.warning(f"获取Schema失败，将使用基础提示: {e}")

        # 构建系统提示词
        system_prompt = build_ai_system_prompt(schema) if schema else """你是一个Neo4j Cypher查询专家。
根据用户的自然语言问题，生成准确的Cypher查询语句。只返回纯净的Cypher查询语句，不要包含任何解释。"""

        # 调用阿里云API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                DASHSCOPE_API_URL,
                headers={
                    'Authorization': f'Bearer {DASHSCOPE_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'qwen3-coder-plus',
                    'messages': [
                        {
                            'role': 'system',
                            'content': system_prompt
                        },
                        {
                            'role': 'user',
                            'content': request.query
                        }
                    ],
                    'temperature': request.temperature,
                    'max_tokens': request.max_tokens
                },
                timeout=30.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"AI服务请求失败: HTTP {response.status_code}"
            )

        # 解析AI响应
        ai_response = response.json()
        if not ai_response.get('choices') or not ai_response['choices']:
            raise HTTPException(status_code=500, detail="AI服务返回空响应")

        raw_cypher = ai_response['choices'][0]['message']['content']

        # 清理生成的Cypher查询
        cleaned_cypher = clean_ai_generated_cypher(raw_cypher)

        generation_time = int((time.time() - start_time) * 1000)

        logger.info(f"生成Cypher查询: {request.query} -> {cleaned_cypher}")

        return NaturalLanguageQueryResponse(
            success=True,
            cypher_query=cleaned_cypher,
            generation_time_ms=generation_time,
            schema_used=bool(schema),
            message="Cypher查询生成成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        generation_time = int((time.time() - start_time) * 1000)
        logger.error(f"自然语言转Cypher失败: {e}")

        return NaturalLanguageQueryResponse(
            success=False,
            cypher_query="",
            generation_time_ms=generation_time,
            schema_used=bool(schema),
            message=f"查询生成失败: {str(e)}"
        )

@app.post("/out/api/intelligent/execute-cypher", response_model=CypherQueryResponse)
async def execute_cypher_query(request: CypherQueryRequest):
    """
    执行Cypher查询接口

    执行用户提供的Cypher查询语句，并返回JSON格式的查询结果。
    支持参数化查询和结果数量限制。

    Args:
        request (CypherQueryRequest): 包含Cypher查询语句和参数

    Returns:
        CypherQueryResponse: 包含查询结果和执行信息

    Raises:
        HTTPException: 当查询执行失败时返回400或500错误

    示例:
        请求: {"cypher": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n LIMIT 10"}
        响应: {"success": true, "records": [...], "count": 10, ...}
    """
    start_time = time.time()

    try:
        # 基本安全检查
        cypher_upper = request.cypher.upper().strip()

        # 禁止危险操作
        dangerous_keywords = ['DELETE', 'CREATE', 'MERGE', 'SET', 'REMOVE', 'DROP']
        if any(keyword in cypher_upper for keyword in dangerous_keywords):
            raise HTTPException(
                status_code=400,
                detail="出于安全考虑，不允许执行修改数据的操作"
            )

        # 添加LIMIT限制（如果指定且查询中没有LIMIT）
        final_cypher = request.cypher
        if request.limit and 'LIMIT' not in cypher_upper:
            final_cypher += f" LIMIT {request.limit}"

        # 执行查询
        with neo4j_driver.session() as session:
            # 转换参数中的整数类型（Neo4j兼容性）
            converted_params = convert_neo4j_integers(request.parameters)

            result = session.run(final_cypher, converted_params)

            # 转换查询结果为JSON格式
            records = []
            for record in result:
                records.append(record_to_dict(record))

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(f"执行Cypher查询: {final_cypher}, 返回 {len(records)} 条记录")

            return CypherQueryResponse(
                success=True,
                records=records,
                count=len(records),
                execution_time_ms=execution_time,
                cypher_query=final_cypher,
                message=f"查询成功，返回 {len(records)} 条记录"
            )

    except HTTPException:
        raise
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        logger.error(f"Cypher查询执行失败: {e}")

        return CypherQueryResponse(
            success=False,
            records=[],
            count=0,
            execution_time_ms=execution_time,
            cypher_query=request.cypher,
            message=f"查询执行失败: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """
    健康检查接口

    用于检查智能查询API服务的运行状态

    Returns:
        Dict: 服务状态信息
    """
    return {
        "status": "healthy",
        "service": "intelligent-query-api",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "/out/api/intelligent/nl-to-cypher",
            "/out/api/intelligent/execute-cypher"
        ]
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化Neo4j连接"""
    init_neo4j()

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    close_neo4j()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    )