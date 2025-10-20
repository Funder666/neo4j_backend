# 智能查询API使用示例

本文档提供智能查询API的详细使用示例，包括两个核心接口的调用方法和响应格式。

## API概览

- **基础URL**: `http://localhost:8000/api/intelligent`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`

## 1. 自然语言转Cypher查询接口

### 端点信息
- **URL**: `/api/intelligent/nl-to-cypher`
- **方法**: POST
- **功能**: 将自然语言描述转换为Neo4j Cypher查询语句

### 请求格式
```json
{
    "query": "自然语言查询描述",
    "include_schema": true,
    "temperature": 0.1,
    "max_tokens": 500
}
```

### 请求参数说明
- `query` (必需): 自然语言查询描述，1-500字符
- `include_schema` (可选): 是否在AI提示中包含Schema信息，默认true
- `temperature` (可选): AI创造性参数，0.0-1.0，默认0.1
- `max_tokens` (可选): AI响应最大token数，50-2000，默认500

### 响应格式
```json
{
    "success": true,
    "cypher_query": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n",
    "generation_time_ms": 1250,
    "schema_used": true,
    "message": "Cypher查询生成成功"
}
```

### 使用示例

#### 示例1: 基础查询
```bash
curl -X POST "http://localhost:8000/api/intelligent/nl-to-cypher" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "查找所有HSK等级为1的汉字"
     }'
```

**响应**:
```json
{
    "success": true,
    "cypher_query": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n",
    "generation_time_ms": 1200,
    "schema_used": true,
    "message": "Cypher查询生成成功"
}
```

#### 示例2: 关系查询
```bash
curl -X POST "http://localhost:8000/api/intelligent/nl-to-cypher" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "找到'喜爱'字的所有近义词",
       "temperature": 0.2
     }'
```

**响应**:
```json
{
    "success": true,
    "cypher_query": "MATCH (n:Word {name: '喜爱'})-[r:NEAR_SYNONYMOUS_WITH]-(m) RETURN n, r, m",
    "generation_time_ms": 950,
    "schema_used": true,
    "message": "Cypher查询生成成功"
}
```

#### 示例3: 复杂条件查询
```bash
curl -X POST "http://localhost:8000/api/intelligent/nl-to-cypher" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "查找笔画数少于5且HSK等级为1-3的汉字"
     }'
```

**响应**:
```json
{
    "success": true,
    "cypher_query": "MATCH (n:Character) WHERE toInteger(n.strokes) < 5 AND n.hskLevel IN ['1', '2', '3'] RETURN n",
    "generation_time_ms": 1400,
    "schema_used": true,
    "message": "Cypher查询生成成功"
}
```

## 2. Cypher查询执行接口

### 端点信息
- **URL**: `/api/intelligent/execute-cypher`
- **方法**: POST
- **功能**: 执行Cypher查询语句并返回JSON格式结果

### 请求格式
```json
{
    "cypher": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n",
    "parameters": {},
    "limit": 50
}
```

### 请求参数说明
- `cypher` (必需): Cypher查询语句，1-2000字符
- `parameters` (可选): 查询参数字典，默认空
- `limit` (可选): 结果数量限制，默认无限制

### 响应格式
```json
{
    "success": true,
    "records": [...],
    "count": 25,
    "execution_time_ms": 45,
    "cypher_query": "MATCH (n:Character) WHERE n.hskLevel = '1' RETURN n LIMIT 50",
    "message": "查询成功，返回 25 条记录"
}
```

### 使用示例

#### 示例1: 简单查询执行
```bash
curl -X POST "http://localhost:8000/api/intelligent/execute-cypher" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "cypher": "MATCH (n:Character) WHERE n.hskLevel = "1" RETURN n.name, n.strokes LIMIT 5"
     }'
```

**响应**:
```json
{
    "success": true,
    "records": [
        {"n.name": "一", "n.strokes": "1"},
        {"n.name": "二", "n.strokes": "2"},
        {"n.name": "三", "n.strokes": "3"},
        {"n.name": "人", "n.strokes": "2"},
        {"n.name": "大", "n.strokes": "3"}
    ],
    "count": 5,
    "execution_time_ms": 23,
    "cypher_query": "MATCH (n:Character) WHERE n.hskLevel = \"1\" RETURN n.name, n.strokes LIMIT 5",
    "message": "查询成功，返回 5 条记录"
}
```

#### 示例2: 参数化查询
```bash
curl -X POST "http://localhost:8000/api/intelligent/execute-cypher" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "cypher": "MATCH (n:Character) WHERE n.hskLevel = $level RETURN n.name LIMIT $limit",
       "parameters": {
         "level": "2",
         "limit": 10
       }
     }'
```

**响应**:
```json
{
    "success": true,
    "records": [
        {"n.name": "你"},
        {"n.name": "我"},
        {"n.name": "他"},
        {"n.name": "她"},
        {"n.name": "们"}
    ],
    "count": 5,
    "execution_time_ms": 18,
    "cypher_query": "MATCH (n:Character) WHERE n.hskLevel = $level RETURN n.name LIMIT $limit",
    "message": "查询成功，返回 5 条记录"
}
```

#### 示例3: 关系查询执行
```bash
curl -X POST "http://localhost:8000/api/intelligent/execute-cypher" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "cypher": "MATCH (n:Word {name: \"喜爱\"})-[r:NEAR_SYNONYMOUS_WITH]-(m) RETURN n.name as source, type(r) as relationship, m.name as target",
       "limit": 10
     }'
```

**响应**:
```json
{
    "success": true,
    "records": [
        {
            "source": "喜爱",
            "relationship": "NEAR_SYNONYMOUS_WITH",
            "target": "爱"
        },
        {
            "source": "喜爱",
            "relationship": "NEAR_SYNONYMOUS_WITH",
            "target": "喜欢"
        }
    ],
    "count": 2,
    "execution_time_ms": 12,
    "cypher_query": "MATCH (n:Word {name: \"喜爱\"})-[r:NEAR_SYNONYMOUS_WITH]-(m) RETURN n.name as source, type(r) as relationship, m.name as target LIMIT 10",
    "message": "查询成功，返回 2 条记录"
}
```

## 3. 组合使用示例

### Python客户端示例
```python
import requests
import json

class IntelligentQueryClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def nl_to_cypher(self, query, **kwargs):
        """自然语言转Cypher"""
        url = f"{self.base_url}/api/intelligent/nl-to-cypher"
        payload = {"query": query, **kwargs}
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()

    def execute_cypher(self, cypher, parameters=None, limit=None):
        """执行Cypher查询"""
        url = f"{self.base_url}/api/intelligent/execute-cypher"
        payload = {"cypher": cypher}
        if parameters:
            payload["parameters"] = parameters
        if limit:
            payload["limit"] = limit
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()

    def intelligent_query(self, natural_language_query, **kwargs):
        """完整的智能查询流程"""
        # 1. 生成Cypher
        nl_result = self.nl_to_cypher(natural_language_query, **kwargs)
        if not nl_result["success"]:
            return nl_result

        # 2. 执行Cypher
        cypher_query = nl_result["cypher_query"]
        exec_result = self.execute_cypher(cypher_query)

        # 3. 组合结果
        return {
            "natural_query": natural_language_query,
            "generated_cypher": cypher_query,
            "generation_time_ms": nl_result["generation_time_ms"],
            "execution_time_ms": exec_result["execution_time_ms"],
            "success": exec_result["success"],
            "records": exec_result["records"],
            "count": exec_result["count"]
        }

# 使用示例
client = IntelligentQueryClient("http://localhost:8000", "your_jwt_token")

# 完整智能查询
result = client.intelligent_query("找到所有HSK等级为1的汉字")
print(f"查询: {result['natural_query']}")
print(f"生成的Cypher: {result['generated_cypher']}")
print(f"结果数量: {result['count']}")
print(f"总耗时: {result['generation_time_ms'] + result['execution_time_ms']}ms")
```

### JavaScript客户端示例
```javascript
class IntelligentQueryClient {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }

    async nlToCypher(query, options = {}) {
        const response = await fetch(`${this.baseUrl}/api/intelligent/nl-to-cypher`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ query, ...options })
        });
        return await response.json();
    }

    async executeCypher(cypher, parameters = {}, limit = null) {
        const payload = { cypher, parameters };
        if (limit) payload.limit = limit;

        const response = await fetch(`${this.baseUrl}/api/intelligent/execute-cypher`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        return await response.json();
    }

    async intelligentQuery(naturalLanguageQuery, options = {}) {
        // 1. 生成Cypher
        const nlResult = await this.nlToCypher(naturalLanguageQuery, options);
        if (!nlResult.success) return nlResult;

        // 2. 执行Cypher
        const execResult = await this.executeCypher(nlResult.cypher_query);

        // 3. 返回组合结果
        return {
            naturalQuery: naturalLanguageQuery,
            generatedCypher: nlResult.cypher_query,
            generationTimeMs: nlResult.generation_time_ms,
            executionTimeMs: execResult.execution_time_ms,
            success: execResult.success,
            records: execResult.records,
            count: execResult.count
        };
    }
}

// 使用示例
const client = new IntelligentQueryClient('http://localhost:8000', 'your_jwt_token');

// 智能查询
client.intelligentQuery('查找笔画数少于5的汉字')
    .then(result => {
        console.log(`查询: ${result.naturalQuery}`);
        console.log(`生成的Cypher: ${result.generatedCypher}`);
        console.log(`结果数量: ${result.count}`);
        console.log(`结果:`, result.records.slice(0, 5)); // 显示前5个结果
    })
    .catch(error => console.error('查询失败:', error));
```

## 4. 错误处理

### 常见错误响应格式
```json
{
    "success": false,
    "cypher_query": "",
    "generation_time_ms": 1200,
    "schema_used": true,
    "message": "查询生成失败: AI服务请求失败: HTTP 500"
}
```

### 错误类型和处理建议

1. **认证错误 (401)**
   - 检查JWT token是否有效
   - 确认token没有过期

2. **参数验证错误 (422)**
   - 检查请求参数格式和范围
   - 确认必需字段都已提供

3. **AI服务错误 (500)**
   - AI服务暂时不可用，稍后重试
   - 检查查询是否过于复杂或模糊

4. **数据库查询错误**
   - 检查生成的Cypher语法是否正确
   - 确认查询的节点和关系在图数据库中存在

5. **安全限制错误**
   - 不允许执行修改数据的操作（CREATE、DELETE等）
   - 调整查询只包含读取操作

## 5. 性能优化建议

1. **合理设置limit参数**，避免返回过多结果
2. **使用参数化查询**，提高查询效率和安全性
3. **启用Schema缓存**，减少重复的Schema获取
4. **批量查询**时考虑并发限制
5. **监控查询性能**，优化复杂查询语句

## 6. 安全注意事项

1. **始终使用HTTPS**进行API调用
2. **妥善保管JWT token**，不要在客户端暴露
3. **验证查询结果**，特别是用户输入的自然语言查询
4. **监控API使用情况**，防止滥用
5. **定期更新认证信息**和API密钥