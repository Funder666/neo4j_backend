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

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import logging
import json
import time
import re
import httpx
import jwt
import pymysql
from datetime import datetime, timedelta
from passlib.context import CryptContext
import uvicorn
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j连接配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "xtxzhu2u"

# 全局Neo4j驱动
neo4j_driver = None

# 阿里云DashScope API配置
DASHSCOPE_API_KEY = "sk-f55b7b2a02a4478fbdcb48c30d90bb49"
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# MySQL数据库配置
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Restart1128",
    "database": "lab_education",
    "port": 3307,
    "charset": "utf8mb4"
}

# JWT配置
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24小时

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

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

# 数据库服务类
class DatabaseService:
    """数据库连接管理服务"""

    def __init__(self):
        self.neo4j_driver = None

    def connect_neo4j(self):
        """初始化Neo4j连接"""
        try:
            self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # 测试连接
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            logger.info("Neo4j连接初始化成功")
            return True
        except Exception as e:
            logger.error(f"Neo4j连接初始化失败: {e}")
            raise

    def get_neo4j_session(self):
        """获取Neo4j会话"""
        if not self.neo4j_driver:
            raise HTTPException(status_code=500, detail="数据库连接未建立")
        return self.neo4j_driver.session()

    def get_mysql_connection(self):
        """获取MySQL连接"""
        try:
            return pymysql.connect(**MYSQL_CONFIG)
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            raise HTTPException(status_code=500, detail="用户数据库连接失败")

    def close_neo4j(self):
        """关闭Neo4j连接"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            logger.info("Neo4j连接已关闭")

# 创建数据库服务实例
db_service = DatabaseService()

def init_neo4j():
    """初始化Neo4j连接"""
    db_service.connect_neo4j()

def close_neo4j():
    """关闭Neo4j连接"""
    db_service.close_neo4j()

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

# 用户认证服务
class AuthService:
    """用户认证服务"""

    @staticmethod
    def get_user_by_username(username: str):
        """根据用户名获取用户信息"""
        try:
            conn = db_service.get_mysql_connection()
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                sql = "SELECT * FROM user_neo4j WHERE username = %s AND status = 'active'"
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
            conn.close()
            return user
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """创建JWT访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

# 简单的用户数据库（用于测试）
TEST_USERS_DB = {
    "admin": {
        "username": "admin",
        "password": "admin2025.",  # 明文密码，实际应用中应该使用hash
        "role": "admin"
    },
    "guest": {
        "username": "guest",
        "password": "guest",
        "role": "user"
    }
}

def verify_password(plain_password: str, stored_password: str) -> bool:
    """验证密码（简单版本，实际应用中应该使用hash验证）"""
    return plain_password == stored_password

def get_user_by_username(username: str):
    """根据用户名获取用户信息"""
    return TEST_USERS_DB.get(username)

# 登录接口
@app.post("/out/api/auth/login")
async def login(user_login: dict):
    """用户登录"""
    user = get_user_by_username(user_login.get("username"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(user_login.get("password"), user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": 1,
            "username": user["username"],
            "role": user["role"]
        }
    }

# 获取当前用户
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """从JWT令牌中获取当前用户信息"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

# 权限查询函数
def get_user_visible_labels(user_role: str) -> List[str]:
    """
    获取用户角色可见的标签列表

    Args:
        user_role (str): 用户角色

    Returns:
        List[str]: 可见的Neo4j标签列表
    """
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT lm.neo4j_name
            FROM label_mappings lm
            LEFT JOIN user_label_permissions ulp ON lm.id = ulp.label_mapping_id
            WHERE lm.is_active = TRUE
                AND lm.type = 'node'
                AND ulp.user_role = %s
                AND ulp.can_view = TRUE
            """
            cursor.execute(sql, (user_role,))
            results = cursor.fetchall()
        conn.close()

        # 返回可见的标签名称列表
        visible_labels = [result['neo4j_name'] for result in results]
        logger.info(f"用户角色 {user_role} 可见的标签: {visible_labels}")
        return visible_labels

    except Exception as e:
        logger.error(f"获取用户可见标签失败: {e}")
        return []  # 出错时返回空列表，确保安全性

def check_label_permission(user_role: str, label_name: str) -> bool:
    """
    检查用户角色对特定标签是否有查看权限

    Args:
        user_role (str): 用户角色
        label_name (str): 标签名称

    Returns:
        bool: 是否有查看权限
    """
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT COUNT(*) as count
            FROM label_mappings lm
            LEFT JOIN user_label_permissions ulp ON lm.id = ulp.label_mapping_id
            WHERE lm.neo4j_name = %s
                AND lm.type = 'node'
                AND lm.is_active = TRUE
                AND ulp.user_role = %s
                AND ulp.can_view = TRUE
            """
            cursor.execute(sql, (label_name, user_role))
            result = cursor.fetchone()
        conn.close()

        return result['count'] > 0

    except Exception as e:
        logger.error(f"检查标签权限失败: {e}")
        return False  # 出错时默认无权限

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

async def get_knowledge_graph_schema(user_role: str = None) -> Dict[str, Any]:
    """
    获取知识图谱的Schema信息

    返回包含节点类型和关系类型信息的字典，用于AI生成准确的Cypher查询
    支持基于用户角色的权限过滤

    Args:
        user_role (str, optional): 用户角色，用于权限过滤

    Returns:
        Dict[str, Any]: 包含node_types和relationship_types的Schema信息

    Raises:
        Exception: 当获取Schema信息失败时
    """
    try:
        # 获取用户可见的标签列表
        visible_labels = None
        if user_role:
            visible_labels = get_user_visible_labels(user_role)
            logger.info(f"为用户角色 {user_role} 获取Schema，可见标签: {visible_labels}")

        with db_service.get_neo4j_session() as session:
            # 获取节点标签信息
            if visible_labels:
                # 有权限过滤的查询
                labels_query = """
                UNWIND $labels AS label
                CALL db.labels() YIELD db_label
                WITH label, db_label
                WHERE db_label = label
                MATCH (n) WHERE db_label IN labels(n)
                RETURN db_label as label, count(n) as count
                ORDER BY count DESC
                """
                labels_result = session.run(labels_query, {"labels": visible_labels})
            else:
                # 无权限过滤的查询（兼容原有逻辑）
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

            schema_data = {
                "node_types": node_types,
                "relationship_types": relationship_types,
                "generated_at": datetime.now().isoformat()
            }

            # 添加权限信息到响应中
            if user_role:
                schema_data["user_role"] = user_role
                schema_data["permission_filtered"] = True
                schema_data["accessible_labels"] = visible_labels
            else:
                schema_data["permission_filtered"] = False

            logger.info(f"成功获取Schema信息，节点类型: {len(node_types)}, 关系类型: {len(relationship_types)}")
            return schema_data

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
async def natural_language_to_cypher(
    request: NaturalLanguageQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    自然语言转Cypher查询接口

    将用户输入的自然语言描述转换为Neo4j Cypher查询语句。
    使用阿里云DashScope API的大语言模型进行智能转换。
    支持基于用户角色的权限控制。

    Args:
        request (NaturalLanguageQueryRequest): 包含自然语言查询和配置参数
        current_user (dict): 当前认证的用户信息

    Returns:
        NaturalLanguageQueryResponse: 包含生成的Cypher查询和相关信息

    Raises:
        HTTPException: 当查询生成失败时返回500错误

    示例:
        请求: {"query": "查找所有HSK等级为1的汉字"}
        响应: {"success": true, "cypher_query": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n", ...}
    """
    start_time = time.time()
    user_role = current_user.get('role', 'user')
    logger.info(f"用户 {current_user['username']} (角色: {user_role}) 请求自然语言转Cypher查询: {request.query}")

    try:
        # 获取知识图谱Schema（如果需要）
        schema = {}
        if request.include_schema:
            try:
                schema = await get_knowledge_graph_schema(user_role)
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

def filter_query_results_by_permission(records: List[Dict], user_role: str) -> List[Dict]:
    """
    根据用户权限过滤查询结果

    Args:
        records (List[Dict]): 查询结果记录
        user_role (str): 用户角色

    Returns:
        List[Dict]: 过滤后的查询结果
    """
    if not records:
        return records

    # 管理员拥有所有权限，不需要过滤
    if user_role == 'admin':
        return records

    # 获取用户可见的标签
    visible_labels = set(get_user_visible_labels(user_role))
    if not visible_labels:
        logger.warning(f"用户角色 {user_role} 没有任何可见标签，返回空结果")
        return []

    filtered_records = []
    filtered_count = 0

    for record in records:
        try:
            filtered_record = {}
            should_include = False

            for key, value in record.items():
                if isinstance(value, dict) and 'labels' in value and 'id' in value:
                    # 这是一个节点对象
                    node_labels = value.get('labels', [])

                    # 检查节点是否有任何可见的标签
                    has_visible_label = any(label in visible_labels for label in node_labels)

                    if has_visible_label:
                        filtered_record[key] = value
                        should_include = True
                    else:
                        filtered_count += 1
                elif isinstance(value, dict) and 'type' in value and 'start_node_id' in value:
                    # 这是一个关系对象，检查其起始和终止节点
                    start_node = value.get('start_node', {})
                    end_node = value.get('end_node', {})

                    start_labels = start_node.get('labels', [])
                    end_labels = end_node.get('labels', [])

                    start_visible = any(label in visible_labels for label in start_labels)
                    end_visible = any(label in visible_labels for label in end_labels)

                    if start_visible and end_visible:
                        filtered_record[key] = value
                        should_include = True
                    else:
                        filtered_count += 1
                else:
                    # 其他类型的值，直接包含
                    filtered_record[key] = value

            if should_include:
                filtered_records.append(filtered_record)

        except Exception as e:
            logger.error(f"过滤查询结果记录时出错: {e}")
            # 出错时保守处理，不包含此记录
            filtered_count += 1

    if filtered_count > 0:
        logger.info(f"用户角色 {user_role} 权限过滤: 移除了 {filtered_count} 条无权限访问的记录")

    return filtered_records

@app.post("/out/api/intelligent/execute-cypher", response_model=CypherQueryResponse)
async def execute_cypher_query(
    request: CypherQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    执行Cypher查询接口

    执行用户提供的Cypher查询语句，并返回JSON格式的查询结果。
    支持参数化查询和结果数量限制。
    支持基于用户角色的权限控制。

    Args:
        request (CypherQueryRequest): 包含Cypher查询语句和参数
        current_user (dict): 当前认证的用户信息

    Returns:
        CypherQueryResponse: 包含查询结果和执行信息

    Raises:
        HTTPException: 当查询执行失败时返回400或500错误

    示例:
        请求: {"cypher": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n LIMIT 10"}
        响应: {"success": true, "records": [...], "count": 10, ...}
    """
    start_time = time.time()
    user_role = current_user.get('role', 'user')
    logger.info(f"用户 {current_user['username']} (角色: {user_role}) 请求执行Cypher查询")

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
        with db_service.get_neo4j_session() as session:
            # 转换参数中的整数类型（Neo4j兼容性）
            converted_params = convert_neo4j_integers(request.parameters)

            result = session.run(final_cypher, converted_params)

            # 转换查询结果为JSON格式
            records = []
            for record in result:
                records.append(record_to_dict(record))

            # 根据用户权限过滤查询结果
            filtered_records = filter_query_results_by_permission(records, user_role)

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(f"执行Cypher查询: {final_cypher}, 原始返回 {len(records)} 条记录, 过滤后 {len(filtered_records)} 条记录")

            return CypherQueryResponse(
                success=True,
                records=filtered_records,
                count=len(filtered_records),
                execution_time_ms=execution_time,
                cypher_query=final_cypher,
                message=f"查询成功，返回 {len(filtered_records)} 条记录" + (f" (共查询到 {len(records)} 条，已按权限过滤)" if len(filtered_records) < len(records) else "")
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

@app.get("/out/api/health")
async def health_check():
    """
    健康检查接口

    用于检查智能查询API服务的运行状态

    Returns:
        Dict: 服务状态信息
    """
    try:
        # 检查数据库连接
        neo4j_status = "disconnected"
        mysql_status = "disconnected"

        # 检查Neo4j连接
        try:
            with db_service.get_neo4j_session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                neo4j_status = "connected" if record["test"] == 1 else "error"
        except Exception as e:
            logger.error(f"Neo4j健康检查失败: {e}")
            neo4j_status = "error"

        # 检查MySQL连接
        try:
            conn = db_service.get_mysql_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            conn.close()
            mysql_status = "connected" if result else "error"
        except Exception as e:
            logger.error(f"MySQL健康检查失败: {e}")
            mysql_status = "error"

        overall_status = "healthy" if neo4j_status == "connected" and mysql_status == "connected" else "unhealthy"

        return {
            "status": overall_status,
            "service": "intelligent-query-api",
            "timestamp": datetime.now().isoformat(),
            "database_status": {
                "neo4j": neo4j_status,
                "mysql": mysql_status
            },
            "features": {
                "jwt_authentication": True,
                "role_based_access_control": True,
                "permission_filtering": True
            },
            "endpoints": [
                "/out/api/auth/login",
                "/out/api/intelligent/nl-to-cypher",
                "/out/api/intelligent/execute-cypher",
                "/out/api/health"
            ]
        }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "service": "intelligent-query-api",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库连接"""
    try:
        init_neo4j()
        logger.info("智能查询API服务启动成功")
    except Exception as e:
        logger.error(f"智能查询API服务启动失败: {e}")
        raise

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    try:
        close_neo4j()
        logger.info("智能查询API服务已关闭")
    except Exception as e:
        logger.error(f"智能查询API服务关闭时出错: {e}")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )