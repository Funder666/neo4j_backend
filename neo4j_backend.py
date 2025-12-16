# -*- coding: utf-8 -*-
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any, Union
import neo4j
from neo4j import GraphDatabase
import logging
import os
import pymysql
import hashlib
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import secrets

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建数据库服务实例
db_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    global db_service
    db_service = DatabaseService()
    db_service.connect_neo4j()
    logger.info("应用启动完成")
    yield
    # 关闭时执行
    if db_service:
        db_service.close_neo4j()
    logger.info("应用关闭完成")

# FastAPI应用初始化
app = FastAPI(
    title="Neo4j Management API",
    description="Neo4j图数据库管理REST API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置信息
NEO4J_URI = "bolt://8.153.207.172:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "xtxzhu2u"

# MySQL配置
MYSQL_CONFIG = {
    "host": "8.153.207.172",
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

# 全局变量
neo4j_driver = None

# Pydantic模型
class NodeCreate(BaseModel):
    labels: List[str]
    properties: Dict[str, Any]

class NodeUpdate(BaseModel):
    properties: Dict[str, Any]

class RelationshipCreate(BaseModel):
    start_node_id: int
    end_node_id: int
    relationship_type: str
    properties: Optional[Dict[str, Any]] = {}

class RelationshipUpdate(BaseModel):
    properties: Dict[str, Any]

class QueryRequest(BaseModel):
    cypher: str
    parameters: Optional[Dict[str, Any]] = {}

class NodeSearchRequest(BaseModel):
    text: str
    label: Optional[str] = None
    limit: Optional[int] = 50
    mode: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "user"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    status: str
    last_login: Optional[datetime]
    created_at: datetime

# 标签映射相关模型
class LabelMapping(BaseModel):
    id: Optional[int] = None
    type: str  # 'node' or 'relationship'
    neo4j_name: str
    display_name: str
    description: Optional[str] = None
    sort_order: Optional[int] = 0

class LabelProperty(BaseModel):
    id: Optional[int] = None
    label_mapping_id: int
    property_key: str
    display_name: str
    description: Optional[str] = None
    data_type: Optional[str] = 'string'
    sort_order: Optional[int] = 0
    is_display: bool = True

# 日志记录相关模型
class QueryLogCreate(BaseModel):
    user_id: int
    user_role: Optional[str] = None
    query_type: str  # 'node_query', 'relationship_query', 'cypher_query', 'smart_query'
    page_name: str
    query_content: Optional[str] = None
    cypher_query: Optional[str] = None
    natural_language_query: Optional[str] = None
    generated_cypher: Optional[str] = None
    satisfaction_rating: Optional[str] = None
    execution_status: str  # 'success', 'error'
    result_count: Optional[int] = 0
    node_count: Optional[int] = 0
    edge_count: Optional[int] = 0
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None

class LabelPermission(BaseModel):
    id: Optional[int] = None
    user_role: str
    label_mapping_id: int
    can_view: bool = True
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

# 用户管理相关模型
class UserManagementCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "user"
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None

class UserManagementUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None

# 标签映射相关模型
class LabelMappingCreate(BaseModel):
    type: str  # 'node' or 'relationship'
    neo4j_name: str
    display_name: str
    description: Optional[str] = None
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True

class LabelMappingUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

# 用户标签权限相关模型
class UserLabelPermissionCreate(BaseModel):
    user_role: str
    label_mapping_id: int
    can_view: Optional[bool] = True
    can_create: Optional[bool] = False
    can_edit: Optional[bool] = False
    can_delete: Optional[bool] = False

class UserLabelPermissionUpdate(BaseModel):
    can_view: Optional[bool] = None
    can_create: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None

# 标签属性相关模型
class LabelPropertyCreate(BaseModel):
    label_mapping_id: int
    property_key: str
    display_name: str
    description: Optional[str] = None
    data_type: Optional[str] = 'string'
    sort_order: Optional[int] = 0
    is_display: Optional[bool] = True

class LabelPropertyUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_display: Optional[bool] = None

# 数据库连接服务
class DatabaseService:
    def __init__(self):
        self.neo4j_driver = None
        self.mysql_connection = None
    
    def connect_neo4j(self):
        try:
            self.neo4j_driver = GraphDatabase.driver(
                NEO4J_URI, 
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                connection_timeout=10,
                max_connection_lifetime=3600,
                max_connection_pool_size=50
            )
            self.neo4j_driver.verify_connectivity()
            logger.info("Neo4j连接成功")
            return True
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            return False
    
    def get_neo4j_session(self):
        if not self.neo4j_driver:
            raise HTTPException(status_code=500, detail="数据库连接未建立")
        return self.neo4j_driver.session()
    
    def get_mysql_connection(self):
        try:
            return pymysql.connect(**MYSQL_CONFIG)
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            raise HTTPException(status_code=500, detail="用户数据库连接失败")
    
    def close_neo4j(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()

    # 日志记录方法
    def create_query_log(self, log_data: QueryLogCreate) -> bool:
        """创建查询日志记录"""
        try:
            conn = self.get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO query_logs (
                    user_id, user_role, query_type, page_name, query_content, cypher_query,
                    natural_language_query, generated_cypher, satisfaction_rating,
                    execution_status, result_count, node_count, edge_count,
                    execution_time_ms, error_message, ip_address
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """
                cursor.execute(sql, (
                    log_data.user_id,
                    log_data.user_role,
                    log_data.query_type,
                    log_data.page_name,
                    log_data.query_content,
                    log_data.cypher_query,
                    log_data.natural_language_query,
                    log_data.generated_cypher,
                    log_data.satisfaction_rating,
                    log_data.execution_status,
                    log_data.result_count,
                    log_data.node_count,
                    log_data.edge_count,
                    log_data.execution_time_ms,
                    log_data.error_message,
                    log_data.ip_address
                ))
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"创建查询日志失败: {e}")
            return False



# 用户认证服务
class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def get_user_by_username(username: str):
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
    def authenticate_user(username: str, password: str):
        user = AuthService.get_user_by_username(username)
        if not user:
            logger.error(f"用户 {username} 不存在")
            return False
        
        logger.info(f"尝试验证用户 {username} 的密码")

        if not AuthService.verify_password(password, user['password_hash']):
            logger.error(f"用户 {username} 密码验证失败")
            return False
        
        # 更新最后登录时间和登录次数
        try:
            conn = db_service.get_mysql_connection()
            with conn.cursor() as cursor:
                sql = """UPDATE user_neo4j SET 
                        last_login = NOW(), 
                        login_count = login_count + 1 
                        WHERE id = %s"""
                cursor.execute(sql, (user['id'],))
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"更新登录信息失败: {e}")
        
        return user

# 获取当前用户
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
    
    user = AuthService.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user

# 工具函数
def record_to_dict(record):
    """将Neo4j记录转换为字典"""
    result = {}
    for key in record.keys():
        value = record[key]
        if hasattr(value, 'id') and hasattr(value, 'labels'):
            # 节点
            result[key] = {
                'id': value.id,
                'labels': list(value.labels),
                'properties': dict(value)
            }
        elif hasattr(value, 'id') and hasattr(value, 'type'):
            # 关系
            result[key] = {
                'id': value.id,
                'type': value.type,
                'start_node_id': value.start_node.id,
                'end_node_id': value.end_node.id,
                'start_node': {
                    'id': value.start_node.id,
                    'labels': list(value.start_node.labels),
                    'properties': dict(value.start_node)
                },
                'end_node': {
                    'id': value.end_node.id,
                    'labels': list(value.end_node.labels),
                    'properties': dict(value.end_node)
                },
                'properties': dict(value)
            }
        else:
            # 其他值
            result[key] = value
    return result

def convert_neo4j_integers(params):
    """将Python整数转换为Neo4j整数"""
    # 在新版本的neo4j驱动中，直接使用Python整数即可
    # 不需要特殊转换
    return params

# API路由

@app.get("/")
async def root():
    return {"message": "Neo4j管理API服务正在运行", "version": "1.0.0"}

# 用户认证相关API
@app.post("/api/auth/login", response_model=Token)
async def login(user_login: UserLogin):
    """用户登录"""
    user = AuthService.authenticate_user(user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=user['id'],
        username=user['username'],
        email=user['email'],
        full_name=user['full_name'],
        role=user['role'],
        status=user['status'],
        last_login=user['last_login'],
        created_at=user['created_at']
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_response
    }

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=current_user['id'],
        username=current_user['username'],
        email=current_user['email'],
        full_name=current_user['full_name'],
        role=current_user['role'],
        status=current_user['status'],
        last_login=current_user['last_login'],
        created_at=current_user['created_at']
    )

@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """用户登出"""
    # 这里可以添加token黑名单逻辑
    return {"message": "登出成功"}

# 健康检查
@app.get("/api/health")
async def health_check():
    """健康检查"""
    try:
        with db_service.get_neo4j_session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库连接异常: {str(e)}")

# Neo4j数据操作API (需要认证)
@app.get("/api/nodes")
async def get_nodes(
    limit: int = Query(50, description="返回数量限制"),
    label: Optional[str] = Query(None, description="节点标签过滤"),
    skip: int = Query(0, description="跳过数量"),
    mode: Optional[str] = Query(None, description="查询模式: general、new-standard、hsk-2.0 或 hsk-3.0"),
    current_user: dict = Depends(get_current_user)
):
    """获取节点列表"""
    try:
        with db_service.get_neo4j_session() as session:
            # 根据模式构建查询
            if mode == 'new-standard' and label:
                # 新标准模式：只返回与InternationalLevel有FROM_LEVEL关系的节点
                if label in ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom', 'Pinyin']:
                    query = f"""
                    MATCH (n:{label})-[:FROM_LEVEL]->(i:InternationalLevel)
                    RETURN n, labels(n) as labels
                    ORDER BY id(n)
                    SKIP $skip
                    LIMIT $limit
                    """
                else:
                    # 其他类型节点正常查询
                    query = f"MATCH (n:{label}) RETURN n, labels(n) as labels ORDER BY id(n) SKIP $skip LIMIT $limit"
            elif mode == 'hsk-2.0' and label:
                # HSK2.0模式：只返回与HSKLevel有FROM_LEVEL关系的节点
                if label in ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom', 'Pinyin']:
                    query = f"""
                    MATCH (n:{label})-[:FROM_LEVEL]->(i:HSKLevel)
                    RETURN n, labels(n) as labels
                    ORDER BY id(n)
                    SKIP $skip
                    LIMIT $limit
                    """
                else:
                    # 其他类型节点正常查询
                    query = f"MATCH (n:{label}) RETURN n, labels(n) as labels ORDER BY id(n) SKIP $skip LIMIT $limit"
            elif mode == 'hsk-3.0' and label:
                # HSK3.0模式：只返回与HSK30Level有FROM_LEVEL关系的节点
                if label in ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom', 'Pinyin']:
                    query = f"""
                    MATCH (n:{label})-[:FROM_LEVEL]->(i:HSK30Level)
                    RETURN n, labels(n) as labels
                    ORDER BY id(n)
                    SKIP $skip
                    LIMIT $limit
                    """
                else:
                    # 其他类型节点正常查询
                    query = f"MATCH (n:{label}) RETURN n, labels(n) as labels ORDER BY id(n) SKIP $skip LIMIT $limit"
            elif label:
                # 通用模式或未指定模式，正常查询
                query = f"MATCH (n:{label}) RETURN n, labels(n) as labels ORDER BY id(n) SKIP $skip LIMIT $limit"
            else:
                query = "MATCH (n) RETURN n, labels(n) as labels ORDER BY id(n) SKIP $skip LIMIT $limit"

            params = convert_neo4j_integers({"limit": limit, "skip": skip})
            result = session.run(query, params)

            nodes = []
            for record in result:
                nodes.append(record_to_dict(record))

            return {"nodes": nodes, "count": len(nodes), "mode": mode}
    except Exception as e:
        logger.error(f"获取节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取节点失败: {str(e)}")

@app.post("/api/nodes/search")
async def search_nodes(
    search_request: NodeSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """搜索节点"""
    try:
        with db_service.get_neo4j_session() as session:
            # 根据模式和标签构建查询
            if search_request.mode == 'new-standard' and search_request.label:
                # 新标准模式：只搜索与InternationalLevel有FROM_LEVEL关系的节点
                if search_request.label in ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom','Pinyin']:
                    # 拼音节点特殊处理,增加 normal_pinyin 字段搜索
                    if search_request.label == 'Pinyin' or search_request.label == 'Syllable':
                        query = f"""
                        MATCH (n:{search_request.label})-[:FROM_LEVEL]->(i:InternationalLevel)
                        WHERE (n.name STARTS WITH $text OR n.value STARTS WITH $text OR n.normal_pinyin STARTS WITH $text
                               OR toString(n.name) STARTS WITH $text OR toString(n.value) STARTS WITH $text OR toString(n.normal_pinyin) STARTS WITH $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                    else:
                        query = f"""
                        MATCH (n:{search_request.label})-[:FROM_LEVEL]->(i:InternationalLevel)
                        WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                else:
                    # 其他类型节点正常搜索
                    if search_request.label == 'Pinyin' or search_request.label == 'Syllable':
                        query = f"""
                        MATCH (n:{search_request.label})
                        WHERE (n.name STARTS WITH $text OR n.value STARTS WITH $text OR n.normal_pinyin STARTS WITH $text
                               OR toString(n.name) STARTS WITH $text OR toString(n.value) STARTS WITH $text OR toString(n.normal_pinyin) STARTS WITH $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                    else:
                        query = f"""
                        MATCH (n:{search_request.label})
                        WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
            elif search_request.mode == 'hsk-2.0' and search_request.label:
                # HSK2.0模式：只搜索与HSKLevel有FROM_LEVEL关系的节点
                if search_request.label in ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom','Pinyin']:
                    # 拼音节点特殊处理,增加 normal_pinyin 字段搜索
                    if search_request.label == 'Pinyin' or search_request.label == 'Syllable':
                        query = f"""
                        MATCH (n:{search_request.label})-[:FROM_LEVEL]->(i:HSKLevel)
                        WHERE (n.name STARTS WITH $text OR n.value STARTS WITH $text OR n.normal_pinyin STARTS WITH $text
                               OR toString(n.name) STARTS WITH $text OR toString(n.value) STARTS WITH $text OR toString(n.normal_pinyin) STARTS WITH $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                    else:
                        query = f"""
                        MATCH (n:{search_request.label})-[:FROM_LEVEL]->(i:HSKLevel)
                        WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                else:
                    # 其他类型节点正常搜索
                    if search_request.label == 'Pinyin' or search_request.label == 'Syllable':
                        query = f"""
                        MATCH (n:{search_request.label})
                        WHERE (n.name STARTS WITH $text OR n.value STARTS WITH $text OR n.normal_pinyin STARTS WITH $text
                               OR toString(n.name) STARTS WITH $text OR toString(n.value) STARTS WITH $text OR toString(n.normal_pinyin) STARTS WITH $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                    else:
                        query = f"""
                        MATCH (n:{search_request.label})
                        WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
            elif search_request.mode == 'hsk-3.0' and search_request.label:
                # HSK3.0模式：只搜索与HSK30Level有FROM_LEVEL关系的节点
                if search_request.label in ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom','Pinyin']:
                    # 拼音节点特殊处理,增加 normal_pinyin 字段搜索
                    if search_request.label == 'Pinyin' or search_request.label == 'Syllable':
                        query = f"""
                        MATCH (n:{search_request.label})-[:FROM_LEVEL]->(i:HSK30Level)
                        WHERE (n.name STARTS WITH $text OR n.value STARTS WITH $text OR n.normal_pinyin STARTS WITH $text
                               OR toString(n.name) STARTS WITH $text OR toString(n.value) STARTS WITH $text OR toString(n.normal_pinyin) STARTS WITH $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                    else:
                        query = f"""
                        MATCH (n:{search_request.label})-[:FROM_LEVEL]->(i:HSK30Level)
                        WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                else:
                    # 其他类型节点正常搜索
                    if search_request.label == 'Pinyin' or search_request.label == 'Syllable':
                        query = f"""
                        MATCH (n:{search_request.label})
                        WHERE (n.name STARTS WITH $text OR n.value STARTS WITH $text OR n.normal_pinyin STARTS WITH $text
                               OR toString(n.name) STARTS WITH $text OR toString(n.value) STARTS WITH $text OR toString(n.normal_pinyin) STARTS WITH $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
                    else:
                        query = f"""
                        MATCH (n:{search_request.label})
                        WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                        RETURN n, labels(n) as labels
                        LIMIT $limit
                        """
            elif search_request.label:
                # 通用模式或未指定模式，正常搜索
                if search_request.label == 'Pinyin' or search_request.label == 'Syllable':
                    query = f"""
                    MATCH (n:{search_request.label})
                    WHERE (n.name STARTS WITH $text OR n.value STARTS WITH $text OR n.normal_pinyin STARTS WITH $text
                           OR toString(n.name) STARTS WITH $text OR toString(n.value) STARTS WITH $text OR toString(n.normal_pinyin) STARTS WITH $text)
                    RETURN n, labels(n) as labels
                    LIMIT $limit
                    """
                else:
                    query = f"""
                    MATCH (n:{search_request.label})
                    WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                    RETURN n, labels(n) as labels
                    LIMIT $limit
                    """
            else:
                query = """
                MATCH (n)
                WHERE (n.name CONTAINS $text OR n.value CONTAINS $text OR toString(n.name) CONTAINS $text OR toString(n.value) CONTAINS $text)
                RETURN n, labels(n) as labels
                LIMIT $limit
                """

            params = convert_neo4j_integers({
                "text": search_request.text,
                "limit": search_request.limit
            })
            result = session.run(query, params)

            nodes = []
            for record in result:
                nodes.append(record_to_dict(record))

            return {"nodes": nodes, "count": len(nodes), "search_text": search_request.text, "mode": search_request.mode}
    except Exception as e:
        logger.error(f"搜索节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索节点失败: {str(e)}")

@app.post("/api/nodes")
async def create_node(
    node: NodeCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建节点"""
    try:
        with db_service.get_neo4j_session() as session:
            labels_str = ":".join(node.labels)
            query = f"CREATE (n:{labels_str} $properties) RETURN n, labels(n) as labels"
            
            result = session.run(query, {"properties": node.properties})
            record = result.single()
            
            if record:
                return {"message": "节点创建成功", "node": record_to_dict(record)}
            else:
                raise HTTPException(status_code=500, detail="节点创建失败")
    except Exception as e:
        logger.error(f"创建节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建节点失败: {str(e)}")

@app.get("/api/nodes/{node_id}")
async def get_node(
    node_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取单个节点"""
    try:
        with db_service.get_neo4j_session() as session:
            query = "MATCH (n) WHERE id(n) = $node_id RETURN n, labels(n) as labels"
            params = convert_neo4j_integers({"node_id": node_id})
            result = session.run(query, params)
            record = result.single()
            
            if record:
                return {"node": record_to_dict(record)}
            else:
                raise HTTPException(status_code=404, detail="节点不存在")
    except Exception as e:
        logger.error(f"获取节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取节点失败: {str(e)}")

@app.put("/api/nodes/{node_id}")
async def update_node(
    node_id: int,
    node: NodeUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新节点"""
    try:
        with db_service.get_neo4j_session() as session:
            query = """
            MATCH (n) WHERE id(n) = $node_id 
            SET n += $properties 
            RETURN n, labels(n) as labels
            """
            params = convert_neo4j_integers({
                "node_id": node_id,
                "properties": node.properties
            })
            result = session.run(query, params)
            record = result.single()
            
            if record:
                return {"message": "节点更新成功", "node": record_to_dict(record)}
            else:
                raise HTTPException(status_code=404, detail="节点不存在")
    except Exception as e:
        logger.error(f"更新节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新节点失败: {str(e)}")

@app.delete("/api/nodes/{node_id}")
async def delete_node(
    node_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除节点"""
    try:
        with db_service.get_neo4j_session() as session:
            # 先检查节点是否存在
            check_query = "MATCH (n) WHERE id(n) = $node_id RETURN n"
            params = convert_neo4j_integers({"node_id": node_id})
            result = session.run(check_query, params)
            
            if not result.single():
                raise HTTPException(status_code=404, detail="节点不存在")
            
            # 删除节点及其关系
            delete_query = "MATCH (n) WHERE id(n) = $node_id DETACH DELETE n"
            session.run(delete_query, params)
            
            return {"message": "节点删除成功", "node_id": node_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除节点失败: {str(e)}")

# 关系相关API
@app.get("/api/relationships")
async def get_relationships(
    limit: int = Query(50, description="返回数量限制"),
    relationship_type: Optional[str] = Query(None, description="关系类型过滤"),
    current_user: dict = Depends(get_current_user)
):
    """获取关系列表"""
    try:
        with db_service.get_neo4j_session() as session:
            if relationship_type:
                query = f"MATCH (n)-[r:{relationship_type}]->(m) RETURN n, r, m LIMIT $limit"
            else:
                query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT $limit"
            
            params = convert_neo4j_integers({"limit": limit})
            result = session.run(query, params)
            
            relationships = []
            nodes = {}  # 用于去重节点
            edges = []  # 关系数据
            
            for record in result:
                record_dict = record_to_dict(record)
                relationships.append(record_dict)
                
                # 提取节点信息
                if 'n' in record_dict:
                    node = record_dict['n']
                    nodes[node['id']] = node
                
                if 'm' in record_dict:
                    node = record_dict['m']
                    nodes[node['id']] = node
                
                # 提取关系信息
                if 'r' in record_dict:
                    rel = record_dict['r']
                    edges.append({
                        'id': rel['id'],
                        'type': rel['type'],
                        'source': rel['start_node_id'],
                        'target': rel['end_node_id'],
                        'properties': rel['properties']
                    })
            
            return {
                "relationships": relationships, 
                "count": len(relationships),
                "nodes": list(nodes.values()),
                "edges": edges,
                "graph_data": {
                    "nodes": list(nodes.values()),
                    "edges": edges
                }
            }
    except Exception as e:
        logger.error(f"获取关系失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取关系失败: {str(e)}")

@app.post("/api/relationships")
async def create_relationship(
    relationship: RelationshipCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建关系"""
    try:
        with db_service.get_neo4j_session() as session:
            query = f"""
            MATCH (start), (end)
            WHERE id(start) = $start_node_id AND id(end) = $end_node_id
            CREATE (start)-[r:{relationship.relationship_type} $properties]->(end)
            RETURN start, r, end
            """
            
            params = convert_neo4j_integers({
                "start_node_id": relationship.start_node_id,
                "end_node_id": relationship.end_node_id,
                "properties": relationship.properties
            })
            result = session.run(query, params)
            record = result.single()
            
            if record:
                return {"message": "关系创建成功", "relationship": record_to_dict(record)}
            else:
                raise HTTPException(status_code=404, detail="起始或终止节点不存在")
    except Exception as e:
        logger.error(f"创建关系失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建关系失败: {str(e)}")

@app.put("/api/relationships/{relationship_id}")
async def update_relationship(
    relationship_id: int,
    relationship: RelationshipUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新关系属性"""
    try:
        with db_service.get_neo4j_session() as session:
            # 先检查关系是否存在
            check_query = "MATCH ()-[r]->() WHERE id(r) = $relationship_id RETURN r"
            params = convert_neo4j_integers({"relationship_id": relationship_id})
            result = session.run(check_query, params)
            
            if not result.single():
                raise HTTPException(status_code=404, detail="关系不存在")
            
            # 更新关系属性
            update_query = """
            MATCH ()-[r]->()
            WHERE id(r) = $relationship_id
            SET r += $properties
            RETURN r
            """
            params = convert_neo4j_integers({
                "relationship_id": relationship_id,
                "properties": relationship.properties
            })
            logger.info(f"更新关系 {relationship_id} 的属性: {relationship.properties}")
            result = session.run(update_query, params)
            record = result.single()
            
            if record:
                return {"message": "关系更新成功", "relationship_id": relationship_id}
            else:
                raise HTTPException(status_code=500, detail="关系更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新关系失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新关系失败: {str(e)}")

@app.delete("/api/relationships/{relationship_id}")
async def delete_relationship(
    relationship_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除关系"""
    try:
        with db_service.get_neo4j_session() as session:
            # 先检查关系是否存在
            check_query = "MATCH ()-[r]->() WHERE id(r) = $relationship_id RETURN r"
            params = convert_neo4j_integers({"relationship_id": relationship_id})
            result = session.run(check_query, params)
            
            if not result.single():
                raise HTTPException(status_code=404, detail="关系不存在")
            
            # 删除关系
            delete_query = "MATCH ()-[r]->() WHERE id(r) = $relationship_id DELETE r"
            session.run(delete_query, params)
            
            return {"message": "关系删除成功", "relationship_id": relationship_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除关系失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除关系失败: {str(e)}")

@app.get("/api/nodes/{node_id}/relationships")
async def get_node_relationships(
    node_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取节点的所有关系（支持新标准节点的引用关系代理查询）"""
    try:
        with db_service.get_neo4j_session() as session:
            # 首先检查是否为新标准节点
            check_query = """
            MATCH (n) WHERE id(n) = $node_id
            RETURN n, labels(n) as node_labels
            """
            params = convert_neo4j_integers({"node_id": node_id})
            check_result = session.run(check_query, params)
            check_record = check_result.single()

            if not check_record:
                raise HTTPException(status_code=404, detail="节点未找到")

            node_labels = check_record["node_labels"]
            is_new_standard = any(label.endswith("NewStandard") for label in node_labels)

            # 所有节点（包括新标准节点）：查询出去和进来的关系，保留方向信息
            # 分别查询出去的关系和进来的关系，确保方向正确
            # 出去的关系：n是查询节点，m是目标节点，关系从n指向m
            outgoing_query = """
            MATCH (n)-[r]->(m)
            WHERE id(n) = $node_id
            RETURN n, r, m, type(r) as relType
            """

            # 进来的关系：m是源节点，n是查询节点，关系从m指向n
            # 返回时保持 n, r, m 的格式，其中n是起始节点，m是查询节点
            incoming_query = """
            MATCH (n)-[r]->(m)
            WHERE id(m) = $node_id
            RETURN n, r, m, type(r) as relType
            """

            # 执行两个查询并合并结果
            outgoing_result = session.run(outgoing_query, params)
            incoming_result = session.run(incoming_query, params)

            relationships = []
            for record in outgoing_result:
                relationships.append(record_to_dict(record))
            for record in incoming_result:
                relationships.append(record_to_dict(record))

            return {
                "relationships": relationships,
                "count": len(relationships),
                "node_id": node_id,
                "is_new_standard": is_new_standard
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取节点关系失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取节点关系失败: {str(e)}")

@app.get("/api/nodes/{node_id}/multi-hop")
async def get_multi_hop_nodes(
    node_id: int,
    hops: int = Query(2, ge=1, le=3, description="跳数：1-3跳"),
    limit: int = Query(10, ge=1, le=50, description="返回节点数量限制"),
    current_user: dict = Depends(get_current_user)
):
    """获取与指定节点多跳相关的节点"""
    try:
        with db_service.get_neo4j_session() as session:
            # 首先检查节点是否存在
            check_query = """
            MATCH (n) WHERE id(n) = $node_id
            RETURN n, labels(n) as node_labels
            """
            params = convert_neo4j_integers({"node_id": node_id, "hops": hops, "limit": limit})
            check_result = session.run(check_query, params)
            check_record = check_result.single()

            if not check_record:
                raise HTTPException(status_code=404, detail="节点未找到")

            # 使用APOC或原生Cypher实现多跳查询
            # 这里使用原生Cypher实现，避免依赖APOC
            multi_hop_query = f"""
            MATCH (start_node) WHERE id(start_node) = $node_id
            MATCH (start_node)-[*1..{hops}]-(end_node)
            WHERE id(start_node) <> id(end_node)  // 排除起始节点本身

            WITH DISTINCT end_node as node, start_node
            ORDER BY rand()  // 随机排序
            LIMIT $limit

            MATCH path = (start_node)-[*1..{hops}]-(node)
            WHERE id(start_node) <> id(node)

            RETURN
                node as target_node,
                labels(node) as target_labels,
                path,
                length(path) as hop_distance,
                [rel in relationships(path) | type(rel)] as relationship_types
            ORDER BY hop_distance  // 优先显示近的节点
            """

            result = session.run(multi_hop_query, params)

            multi_hop_data = []
            processed_nodes = set()  # 用于去重

            for record in result:
                target_node = record["target_node"]
                node_id_val = target_node.id

                # 避免重复节点
                if node_id_val in processed_nodes:
                    continue
                processed_nodes.add(node_id_val)

                # 转换节点数据
                node_data = {
                    'id': node_id_val,
                    'labels': list(record["target_labels"]),
                    'properties': dict(target_node),
                    'hop_distance': record["hop_distance"],
                    'relationship_types': record["relationship_types"],
                    'path': record_to_dict(record)["path"] if "path" in record_to_dict(record) else None
                }

                multi_hop_data.append(node_data)

            # 获取起始节点信息
            start_record = check_record["n"]
            start_node_data = {
                "id": start_record.id,
                "labels": list(start_record.labels),
                "properties": dict(start_record)
            }

            return {
                "start_node": start_node_data,
                "multi_hop_nodes": multi_hop_data,
                "count": len(multi_hop_data),
                "hops": hops,
                "limit": limit
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取多跳节点失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取多跳节点失败: {str(e)}")

# 图数据API
@app.get("/api/graph")
async def get_graph_data(
    limit: int = Query(100, description="返回数量限制"),
    current_user: dict = Depends(get_current_user)
):
    """获取图数据（用于可视化）"""
    try:
        with db_service.get_neo4j_session() as session:
            query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT $limit"
            params = convert_neo4j_integers({"limit": limit})
            result = session.run(query, params)
            
            graph_data = []
            for record in result:
                graph_data.append(record_to_dict(record))
            
            return {"graph_data": graph_data, "count": len(graph_data)}
    except Exception as e:
        logger.error(f"获取图数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取图数据失败: {str(e)}")

# 元数据API
@app.get("/api/labels/neo4j")
async def get_all_labels(current_user: dict = Depends(get_current_user)):
    """获取所有标签（兼容接口，支持返回数量）"""
    try:
        with db_service.get_neo4j_session() as session:
            # 首先获取基础标签列表
            labels_query = "CALL db.labels()"
            labels_result = session.run(labels_query)
            
            labels = []
            for record in labels_result:
                labels.append(record["label"])
            
            # 获取每个标签的节点数量
            count_query = "MATCH (n) UNWIND labels(n) AS label RETURN label, count(n) as count"
            count_result = session.run(count_query)
            
            count_map = {}
            for record in count_result:
                count_map[record["label"]] = record["count"]
            
            # 创建带数量的标签列表
            labels_with_counts = []
            for label in labels:
                labels_with_counts.append({
                    "label": label,
                    "count": count_map.get(label, 0)
                })
            
            return {
                "labels": labels, 
                "labels_with_counts": labels_with_counts,
                "count": len(labels)
            }
    except Exception as e:
        logger.error(f"获取标签失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取标签失败: {str(e)}")

@app.get("/api/relationship-types")
async def get_relationship_types(
    mode: Optional[str] = Query(None, description="查询模式: general、new-standard、hsk-2.0 或 hsk-3.0"),
    current_user: dict = Depends(get_current_user)
):
    """获取所有关系类型"""
    try:
        with db_service.get_neo4j_session() as session:
            if mode == 'new-standard':
                # 新标准模式：
                # 起始节点必须与InternationalLevel有FROM_LEVEL关系
                # 并且终止节点要么与InternationalLevel有FROM_LEVEL关系,要么是特定等级节点
                query = """
                MATCH (n)-[r]->(m)
                WHERE EXISTS((n)-[:FROM_LEVEL]->(:InternationalLevel))
                  AND (EXISTS((m)-[:FROM_LEVEL]->(:InternationalLevel))
                       OR m:InternationalLevel
                       OR m:CulturalStage
                       OR m:CulturalLevel1
                       OR m:CulturalLevel2)
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
                """
            elif mode == 'hsk-2.0':
                # HSK2.0模式：
                # 起始节点必须与HSKLevel有FROM_LEVEL关系
                # 并且终止节点要么与HSKLevel有FROM_LEVEL关系,要么是特定等级节点
                query = """
                MATCH (n)-[r]->(m)
                WHERE EXISTS((n)-[:FROM_LEVEL]->(:HSKLevel))
                  AND (EXISTS((m)-[:FROM_LEVEL]->(:HSKLevel))
                       OR m:HSKLevel
                       OR m:CulturalStage
                       OR m:CulturalLevel1
                       OR m:CulturalLevel2)
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
                """
            elif mode == 'hsk-3.0':
                # HSK3.0模式：
                # 起始节点必须与HSK30Level有FROM_LEVEL关系
                # 并且终止节点要么与HSK30Level有FROM_LEVEL关系,要么是特定等级节点
                query = """
                MATCH (n)-[r]->(m)
                WHERE EXISTS((n)-[:FROM_LEVEL]->(:HSK30Level))
                  AND (EXISTS((m)-[:FROM_LEVEL]->(:HSK30Level))
                       OR m:HSK30Level
                       OR m:CulturalStage
                       OR m:CulturalLevel1
                       OR m:CulturalLevel2)
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
                """
            else:
                # 通用模式：统计所有关系
                query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"

            result = session.run(query)

            types = []
            for record in result:
                types.append({
                    "type": record["type"],
                    "count": record["count"]
                })

            return {"relationship_types": types, "count": len(types), "mode": mode}
    except Exception as e:
        logger.error(f"获取关系类型失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取关系类型失败: {str(e)}")

@app.get("/api/node-types")
async def get_node_types(
    mode: Optional[str] = Query(None, description="查询模式: general、new-standard、hsk-2.0 或 hsk-3.0"),
    current_user: dict = Depends(get_current_user)
):
    """获取所有节点标签及其数量"""
    try:
        with db_service.get_neo4j_session() as session:
            if mode == 'new-standard':
                # 新标准模式：分别统计有FROM_LEVEL关系的节点和其他相关节点
                query = """
                MATCH (n)-[:FROM_LEVEL]->(i:InternationalLevel)
                UNWIND labels(n) AS label
                WITH label, count(n) as count
                WHERE label IN ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom', 'Pinyin']
                RETURN label, count

                UNION ALL

                MATCH (n)
                UNWIND labels(n) AS label
                WITH label, count(n) as count
                WHERE label IN ['Radical', 'CulturalStage', 'CulturalLevel1', 'CulturalLevel2', 'InternationalLevel', 'Error']
                RETURN label, count

                ORDER BY count DESC
                """
            elif mode == 'hsk-2.0':
                # HSK2.0模式：分别统计有FROM_LEVEL关系的节点和其他相关节点
                query = """
                MATCH (n)-[:FROM_LEVEL]->(i:HSKLevel)
                UNWIND labels(n) AS label
                WITH label, count(n) as count
                WHERE label IN ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom', 'Pinyin']
                RETURN label, count

                UNION ALL

                MATCH (n)
                UNWIND labels(n) AS label
                WITH label, count(n) as count
                WHERE label IN ['Radical', 'CulturalStage', 'CulturalLevel1', 'CulturalLevel2', 'HSKLevel', 'Error']
                RETURN label, count

                ORDER BY count DESC
                """
            elif mode == 'hsk-3.0':
                # HSK3.0模式：分别统计有FROM_LEVEL关系的节点和其他相关节点
                query = """
                MATCH (n)-[:FROM_LEVEL]->(i:HSK30Level)
                UNWIND labels(n) AS label
                WITH label, count(n) as count
                WHERE label IN ['Character', 'Word', 'Grammar', 'Cultural', 'Question', 'Idiom', 'Pinyin']
                RETURN label, count

                UNION ALL

                MATCH (n)
                UNWIND labels(n) AS label
                WITH label, count(n) as count
                WHERE label IN ['Radical', 'CulturalStage', 'CulturalLevel1', 'CulturalLevel2', 'HSK30Level', 'Error']
                RETURN label, count

                ORDER BY count DESC
                """
            else:
                # 通用模式：统计所有节点
                query = "MATCH (n) UNWIND labels(n) AS label RETURN label, count(n) as count ORDER BY count DESC"

            result = session.run(query)

            types = []
            for record in result:
                types.append({
                    "label": record["label"],
                    "count": record["count"]
                })

            return {"node_types": types, "count": len(types), "mode": mode}
    except Exception as e:
        logger.error(f"获取节点类型失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取节点类型失败: {str(e)}")

# 自定义查询API
@app.post("/api/query")
async def run_custom_query(
    query_request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """执行自定义Cypher查询"""
    try:
        import asyncio
        from concurrent.futures import TimeoutError

        with db_service.get_neo4j_session() as session:
            # 简单直接的查询语句清理
            original_query = query_request.cypher

            # 直接将所有换行符替换为空格
            cleaned_query = original_query.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # 去除多余空格
            cleaned_query = ' '.join(cleaned_query.split())

            # 检查查询是否包含LIMIT，如果没有则警告并自动添加
            cypher_query_upper = cleaned_query.strip().upper()

            # 使用正则表达式检查是否已经有完整的LIMIT子句
            limit_pattern = r'\bLIMIT\s+\d+\s*$'
            has_limit = re.search(limit_pattern, cleaned_query, re.IGNORECASE)

            if not has_limit and 'RETURN' in cypher_query_upper:
                logger.warning(f"查询未包含LIMIT限制，可能影响性能: {cleaned_query}")
                # 为没有LIMIT的查询自动添加合理的限制
                modified_query = cleaned_query + ' LIMIT 1000'
                logger.info(f"为查询自动添加LIMIT 1000: {modified_query}")
                final_query = modified_query
            else:
                final_query = cleaned_query
                logger.info(f"使用清理后的查询: {final_query}")

            params = convert_neo4j_integers(query_request.parameters)

            # 确保使用处理后的查询
            query_request.cypher = final_query

            # 使用异步方式执行查询，设置10秒超时
            def run_query():
                return session.run(query_request.cypher, params)

            # 设置10秒超时
            try:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, run_query),
                    timeout=10.0  # 10秒超时
                )
            except asyncio.TimeoutError:
                logger.error(f"查询超时: {query_request.cypher}")
                raise HTTPException(
                    status_code=408,
                    detail="查询执行超时，请简化查询条件或添加LIMIT限制"
                )
            
            records = []
            for record in result:
                records.append(record_to_dict(record))
            
            # 检查是否是图形查询（包含节点和关系）
            has_nodes = any('id' in record and 'labels' in record for record in records if isinstance(record, dict))
            has_relationships = any('type' in record and 'start_node_id' in record for record in records if isinstance(record, dict))
            
            # 如果查询结果包含节点和关系，提供图形数据格式
            graph_data = None
            if has_nodes or has_relationships:
                nodes_map = {}
                edges = []
                
                for record in records:
                    for key, value in record.items():
                        if isinstance(value, dict):
                            # 处理节点
                            if 'labels' in value and 'properties' in value:
                                node_id = value.get('id')
                                if node_id is not None:
                                    nodes_map[node_id] = {
                                        'id': node_id,
                                        'labels': value['labels'],
                                        'properties': value['properties']
                                    }
                            # 处理关系
                            elif 'type' in value and 'start_node_id' in value and 'end_node_id' in value:
                                edges.append({
                                    'id': value.get('id'),
                                    'type': value['type'],
                                    'source': value['start_node_id'],
                                    'target': value['end_node_id'],
                                    'properties': value.get('properties', {})
                                })
                
                if nodes_map or edges:
                    graph_data = {
                        'nodes': list(nodes_map.values()),
                        'edges': edges
                    }
            
            return {
                "records": records, 
                "count": len(records),
                "graph_data": graph_data,
                "query": query_request.cypher,
                "parameters": query_request.parameters
            }
    except Exception as e:
        logger.error(f"自定义查询失败: {e}")
        # 提供更详细的错误信息
        error_detail = str(e)
        if "SyntaxError" in error_detail:
            error_detail = f"Cypher语法错误: {error_detail}"
        elif "ConstraintValidationFailed" in error_detail:
            error_detail = f"约束验证失败: {error_detail}"
        elif "ClientError" in error_detail:
            error_detail = f"查询错误: {error_detail}"
        
        raise HTTPException(status_code=400, detail=error_detail)

# 统计信息API
@app.get("/api/stats")
async def get_database_stats(current_user: dict = Depends(get_current_user)):
    """获取数据库统计信息"""
    try:
        with db_service.get_neo4j_session() as session:
            # 获取节点数量
            node_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_result.single()["count"]
            
            # 获取关系数量
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()["count"]
            
            # 获取标签数量
            label_result = session.run("CALL db.labels() YIELD label RETURN count(label) as count")
            label_count = label_result.single()["count"]
            
            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "label_count": label_count
            }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

# ================== 标签映射和权限控制API ==================

# 获取用户可见的标签映射
@app.get("/api/labels/mappings")
async def get_label_mappings(
    type: Optional[str] = Query(None, description="标签类型: node 或 relationship"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户角色可见的标签映射"""
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 首先查询所有激活的标签映射
            sql = """
            SELECT
                lm.id, lm.type, lm.neo4j_name, lm.display_name,
                lm.description, lm.sort_order
            FROM label_mappings lm
            WHERE lm.is_active = TRUE
            """
            params = []

            if type:
                sql += " AND lm.type = %s"
                params.append(type)

            sql += " ORDER BY lm.sort_order, lm.display_name"

            cursor.execute(sql, params)
            mappings = cursor.fetchall()

            # 查询用户的权限配置
            if mappings:
                label_ids = [m['id'] for m in mappings]
                placeholders = ','.join(['%s'] * len(label_ids))

                permission_sql = f"""
                SELECT label_mapping_id, can_view, can_create, can_edit, can_delete
                FROM user_label_permissions
                WHERE user_role = %s AND label_mapping_id IN ({placeholders})
                """
                permission_params = [current_user['role']] + label_ids

                cursor.execute(permission_sql, permission_params)
                permissions = cursor.fetchall()

                # 创建权限映射字典
                permission_map = {}
                for p in permissions:
                    permission_map[p['label_mapping_id']] = {
                        'can_view': bool(p['can_view']),
                        'can_create': bool(p['can_create']),
                        'can_edit': bool(p['can_edit']),
                        'can_delete': bool(p['can_delete'])
                    }

            # 转换为字典，按类型分组
            result = {
                'node_labels': [],
                'relationship_labels': []
            }

            for mapping in mappings:
                # 获取权限，如果没有配置权限，管理员默认有所有权限，其他用户默认有查看权限
                permission = permission_map.get(mapping['id'], {
                    'can_view': True,
                    'can_create': current_user['role'] == 'admin',
                    'can_edit': current_user['role'] == 'admin',
                    'can_delete': current_user['role'] == 'admin'
                })

                target_list = 'node_labels' if mapping['type'] == 'node' else 'relationship_labels'
                result[target_list].append({
                    'id': mapping['id'],
                    'neo4j_name': mapping['neo4j_name'],
                    'display_name': mapping['display_name'],
                    'description': mapping['description'],
                    'sort_order': mapping['sort_order'],
                    'permissions': permission
                })

            return result

    except Exception as e:
        logger.error(f"获取标签映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取标签映射失败: {str(e)}")
    finally:
        conn.close()

# 获取标签属性信息
@app.get("/api/labels/{label_mapping_id}/properties")
async def get_label_properties(
    label_mapping_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取指定标签的属性信息，基于用户标签权限过滤"""
    logger.info(f"请求获取标签 {label_mapping_id} 的属性信息")
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 首先检查用户是否有该标签的查看权限
            permission_sql = """
            SELECT can_view, can_edit FROM user_label_permissions
            WHERE label_mapping_id = %s AND user_role = %s
            """
            cursor.execute(permission_sql, (label_mapping_id, current_user['role']))
            label_permission = cursor.fetchone()

            # 如果没有权限配置，管理员默认有所有权限
            if not label_permission:
                if current_user['role'] == 'admin':
                    label_permission = {'can_view': True, 'can_edit': True}
                else:
                    label_permission = {'can_view': True, 'can_edit': False}
            else:
                # 确保权限值是布尔类型
                label_permission['can_view'] = bool(label_permission['can_view'])
                label_permission['can_edit'] = bool(label_permission['can_edit'])

            if not label_permission['can_view']:
                return {'properties': []}
            
            # 获取该标签的属性信息
            properties_sql = """
            SELECT
                property_key, display_name, description, data_type, sort_order, is_display
            FROM label_properties
            WHERE label_mapping_id = %s AND is_display = TRUE
            ORDER BY sort_order, property_key
            """
            cursor.execute(properties_sql, (label_mapping_id,))
            properties = cursor.fetchall()

            # 确保数据类型正确
            for prop in properties:
                prop['is_display'] = bool(prop['is_display'])

            # 为每个属性添加权限信息
            for prop in properties:
                prop['can_view'] = True  # 如果能查询到，说明有查看权限
                prop['can_edit'] = bool(label_permission['can_edit'])  # 编辑权限基于标签权限
            
            return {'properties': properties}
            
    except Exception as e:
        logger.error(f"获取标签属性失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取标签属性失败: {str(e)}")
    finally:
        conn.close()

# 根据标签名称获取显示名称
@app.get("/api/labels/display-name/{neo4j_name}")
async def get_display_name(
    neo4j_name: str,
    type: str = Query(..., description="标签类型: node 或 relationship"),
    current_user: dict = Depends(get_current_user)
):
    """根据Neo4j标签名称获取显示名称"""
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT lm.display_name, lm.description
            FROM label_mappings lm
            LEFT JOIN user_label_permissions ulp ON lm.id = ulp.label_mapping_id
            WHERE lm.neo4j_name = %s AND lm.type = %s AND lm.is_active = TRUE
                AND ulp.user_role = %s AND ulp.can_view = TRUE
            """
            cursor.execute(sql, (neo4j_name, type, current_user['role']))
            result = cursor.fetchone()
            
            if not result:
                # 如果没有找到映射，返回原始名称
                return {
                    'neo4j_name': neo4j_name,
                    'display_name': neo4j_name,
                    'description': None,
                }
            
            return {
                'neo4j_name': neo4j_name,
                'display_name': result['display_name'],
                'description': result['description'],
            }
            
    except Exception as e:
        logger.error(f"获取显示名称失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取显示名称失败: {str(e)}")
    finally:
        conn.close()

# 管理员API - 创建标签映射
@app.post("/api/admin/labels/mappings")
async def create_label_mapping(
    mapping: LabelMapping,
    current_user: dict = Depends(get_current_user)
):
    """创建标签映射（仅管理员）"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="需要管理员权限")
        
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            # 插入标签映射
            sql = """
            INSERT INTO label_mappings 
            (type, neo4j_name, display_name, description, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                mapping.type, mapping.neo4j_name, mapping.display_name,
                mapping.description, mapping.sort_order
            ))
            mapping_id = cursor.lastrowid
            
            # 为所有角色创建默认权限
            roles = ['admin', 'user1', 'user2', 'user3', 'user4']
            for role in roles:
                perm_sql = """
                INSERT INTO user_label_permissions 
                (user_role, label_mapping_id, can_view, can_create, can_edit, can_delete)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                if role == 'admin':
                    cursor.execute(perm_sql, (role, mapping_id, True, True, True, True))
                else:
                    # 普通用户默认只有查看权限，需要管理员后续手动分配具体权限
                    cursor.execute(perm_sql, (role, mapping_id, False, False, False, False))
            
            conn.commit()
            return {"id": mapping_id, "message": "标签映射创建成功"}
            
    except Exception as e:
        conn.rollback()
        logger.error(f"创建标签映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建标签映射失败: {str(e)}")
    finally:
        conn.close()

# 管理员API - 更新标签属性
@app.put("/api/admin/labels/properties")
async def update_label_properties(
    properties: List[LabelProperty],
    current_user: dict = Depends(get_current_user)
):
    """批量更新标签属性（仅管理员）"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="需要管理员权限")
        
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            for prop in properties:
                sql = """
                INSERT INTO label_properties 
                (label_mapping_id, property_key, display_name, description, data_type, 
                 sort_order, is_display)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                display_name = VALUES(display_name),
                description = VALUES(description),
                data_type = VALUES(data_type),
                sort_order = VALUES(sort_oørder),
                is_display = VALUES(is_display)
                """
                cursor.execute(sql, (
                    prop.label_mapping_id, prop.property_key, prop.display_name,
                    prop.description, prop.data_type, prop.sort_order, prop.is_display
                ))
            
            conn.commit()
            return {"message": f"成功更新 {len(properties)} 个标签属性"}
            
    except Exception as e:
        conn.rollback()
        logger.error(f"更新标签属性失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新标签属性失败: {str(e)}")
    finally:
        conn.close()


# 日志记录API接口
@app.post("/api/logs/query")
async def create_query_log(
    request: Request,
    log_data: QueryLogCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建查询日志记录"""
    try:
        # 自动获取请求信息
        log_data.ip_address = request.client.host

        # 使用当前用户ID和角色
        log_data.user_id = current_user["id"]
        log_data.user_role = current_user.get("role", "user")

        success = db_service.create_query_log(log_data)
        if success:
            return {"message": "日志记录成功", "success": True}
        else:
            return {"message": "日志记录失败", "success": False}
    except Exception as e:
        logger.error(f"创建查询日志API失败: {e}")
        raise HTTPException(status_code=500, detail=f"日志记录失败: {str(e)}")



@app.patch("/api/logs/query/{log_id}/satisfaction")
async def update_satisfaction_rating(
    log_id: int,
    satisfaction_rating: str,
    current_user: dict = Depends(get_current_user)
):
    """更新查询日志的满意度评价"""
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            sql = """
            UPDATE query_logs
            SET satisfaction_rating = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """
            cursor.execute(sql, (satisfaction_rating, log_id, current_user["id"]))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="未找到对应的日志记录")
            conn.commit()
        conn.close()
        return {"message": "满意度评价更新成功", "success": True}
    except Exception as e:
        logger.error(f"更新满意度评价失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新满意度评价失败: {str(e)}")



# ==================== 用户管理API ====================

@app.get("/api/users")
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    role: Optional[str] = Query(None, description="用户角色筛选"),
    status: Optional[str] = Query(None, description="用户状态筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户列表（分页）"""
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # 构建查询条件
            where_conditions = []
            params = []

            if status:
                # 如果指定了status，则显示指定状态的用户
                where_conditions.append("status = %s")
                params.append(status)

            if role:
                where_conditions.append("role = %s")
                params.append(role)

            if search:
                where_conditions.append("(username LIKE %s OR full_name LIKE %s OR email LIKE %s)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            # 查询总数
            count_sql = f"SELECT COUNT(*) as total FROM user_neo4j {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            # 查询数据
            offset = (page - 1) * size
            sql = f"""
            SELECT id, username, email, full_name, role, status, avatar_url, phone,
                   department, position, last_login, login_count, created_at, updated_at
            FROM user_neo4j
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, params + [size, offset])
            users = cursor.fetchall()

        conn.close()

        return {
            "items": users,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")

@app.post("/api/users")
async def create_user(
    user_data: UserManagementCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新用户"""
    try:
        # 检查当前用户权限（只有admin可以创建用户）
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            # 检查用户名和邮箱是否已存在
            check_sql = "SELECT id FROM user_neo4j WHERE username = %s OR email = %s"
            cursor.execute(check_sql, (user_data.username, user_data.email))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

            # 密码加密
            password_hash = AuthService.get_password_hash(user_data.password)

            # 插入新用户
            sql = """
            INSERT INTO user_neo4j (
                username, email, password_hash, full_name, role,
                department, position, phone, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                user_data.username,
                user_data.email,
                password_hash,
                user_data.full_name,
                user_data.role,
                user_data.department,
                user_data.position,
                user_data.phone,
                current_user["id"]
            ))
            user_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return {"message": "用户创建成功", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")

@app.put("/api/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserManagementUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新用户信息"""
    try:
        # 检查权限
        if current_user.get("role") != "admin" and current_user["id"] != user_id:
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            # 构建更新字段
            update_fields = []
            params = []

            if user_data.email is not None:
                update_fields.append("email = %s")
                params.append(user_data.email)

            if user_data.full_name is not None:
                update_fields.append("full_name = %s")
                params.append(user_data.full_name)

            if user_data.role is not None and current_user.get("role") == "admin":
                update_fields.append("role = %s")
                params.append(user_data.role)

            if user_data.department is not None:
                update_fields.append("department = %s")
                params.append(user_data.department)

            if user_data.position is not None:
                update_fields.append("position = %s")
                params.append(user_data.position)

            if user_data.phone is not None:
                update_fields.append("phone = %s")
                params.append(user_data.phone)

            if user_data.status is not None and current_user.get("role") == "admin":
                update_fields.append("status = %s")
                params.append(user_data.status)

            update_fields.append("updated_at = NOW()")
            params.append(user_id)

            if update_fields:
                sql = f"UPDATE user_neo4j SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(sql, params)
                conn.commit()

        conn.close()
        return {"message": "用户信息更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")

@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除用户（硬删除）"""
    try:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        if current_user["id"] == user_id:
            raise HTTPException(status_code=400, detail="不能删除自己的账号")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            # 先删除相关的权限数据
            cursor.execute("DELETE FROM user_label_permissions WHERE user_role = (SELECT role FROM user_neo4j WHERE id = %s)", (user_id,))

            # 硬删除用户
            sql = "DELETE FROM user_neo4j WHERE id = %s"
            cursor.execute(sql, (user_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="用户不存在")
            conn.commit()

        conn.close()
        return {"message": "用户删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")

# ==================== 标签映射管理API ====================

@app.get("/api/labels")
async def get_label_mappings(
    type: Optional[str] = Query(None, description="标签类型：node/relationship"),
    current_user: dict = Depends(get_current_user)
):
    """获取标签映射列表"""
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT id, type, neo4j_name, display_name, description,
                   sort_order, is_active, created_at, updated_at
            FROM label_mappings
            """
            params = []
            if type:
                sql += " WHERE type = %s"
                params.append(type)

            sql += " ORDER BY type, sort_order, display_name"
            cursor.execute(sql, params)
            labels = cursor.fetchall()

            # 确保数据类型正确，特别是 is_active 字段
            for label in labels:
                # 将 tinyint 转换为布尔值
                label['is_active'] = bool(label['is_active'])
                # 确保日期时间格式正确
                if label.get('created_at'):
                    label['created_at'] = label['created_at'].isoformat()
                if label.get('updated_at'):
                    label['updated_at'] = label['updated_at'].isoformat()

        conn.close()
        return labels
    except Exception as e:
        logger.error(f"获取标签映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取标签映射失败: {str(e)}")

@app.post("/api/labels")
async def create_label_mapping(
    label_data: LabelMappingCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建标签映射"""
    try:
        if current_user.get("role") not in ["admin", "editor"]:
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO label_mappings (
                type, neo4j_name, display_name, description,
                sort_order, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                label_data.type,
                label_data.neo4j_name,
                label_data.display_name,
                label_data.description,
                label_data.sort_order,
                label_data.is_active
            ))
            label_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return {"message": "标签映射创建成功", "label_id": label_id}
    except Exception as e:
        logger.error(f"创建标签映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建标签映射失败: {str(e)}")

@app.put("/api/labels/{label_id}")
async def update_label_mapping(
    label_id: int,
    label_data: LabelMappingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新标签映射"""
    try:
        if current_user.get("role") not in ["admin", "editor"]:
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            update_fields = []
            params = []

            if label_data.display_name is not None:
                update_fields.append("display_name = %s")
                params.append(label_data.display_name)

            if label_data.description is not None:
                update_fields.append("description = %s")
                params.append(label_data.description)

            if label_data.sort_order is not None:
                update_fields.append("sort_order = %s")
                params.append(label_data.sort_order)

            if label_data.is_active is not None:
                update_fields.append("is_active = %s")
                params.append(label_data.is_active)

            update_fields.append("updated_at = NOW()")
            params.append(label_id)

            if update_fields:
                sql = f"UPDATE label_mappings SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(sql, params)
                conn.commit()

        conn.close()
        return {"message": "标签映射更新成功"}
    except Exception as e:
        logger.error(f"更新标签映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新标签映射失败: {str(e)}")

@app.delete("/api/labels/{label_id}")
async def delete_label_mapping(
    label_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除标签映射"""
    try:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            sql = "DELETE FROM label_mappings WHERE id = %s"
            cursor.execute(sql, (label_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="标签映射不存在")
            conn.commit()

        conn.close()
        return {"message": "标签映射删除成功"}
    except Exception as e:
        logger.error(f"删除标签映射失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除标签映射失败: {str(e)}")

# ==================== 用户标签权限管理API ====================

@app.get("/api/user-label-permissions")
async def get_user_label_permissions(
    role: Optional[str] = Query(None, description="用户角色"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户标签权限列表"""
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT p.*, l.type, l.neo4j_name, l.display_name as label_display_name
            FROM user_label_permissions p
            JOIN label_mappings l ON p.label_mapping_id = l.id
            """
            params = []
            if role:
                sql += " WHERE p.user_role = %s"
                params.append(role)

            sql += " ORDER BY p.user_role, l.type, l.display_name"
            cursor.execute(sql, params)
            permissions = cursor.fetchall()

            # 确保数据类型正确
            for permission in permissions:
                # 将 tinyint 转换为布尔值
                permission['can_view'] = bool(permission['can_view'])
                permission['can_create'] = bool(permission['can_create'])
                permission['can_edit'] = bool(permission['can_edit'])
                permission['can_delete'] = bool(permission['can_delete'])

        conn.close()
        return permissions
    except Exception as e:
        logger.error(f"获取用户标签权限失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户标签权限失败: {str(e)}")

@app.post("/api/user-label-permissions")
async def create_user_label_permission(
    permission_data: UserLabelPermissionCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建用户标签权限"""
    try:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO user_label_permissions (
                user_role, label_mapping_id, can_view, can_create, can_edit, can_delete
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            can_view = VALUES(can_view),
            can_create = VALUES(can_create),
            can_edit = VALUES(can_edit),
            can_delete = VALUES(can_delete),
            updated_at = NOW()
            """
            cursor.execute(sql, (
                permission_data.user_role,
                permission_data.label_mapping_id,
                permission_data.can_view,
                permission_data.can_create,
                permission_data.can_edit,
                permission_data.can_delete
            ))
            conn.commit()

        conn.close()
        return {"message": "用户标签权限设置成功"}
    except Exception as e:
        logger.error(f"创建用户标签权限失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建用户标签权限失败: {str(e)}")

@app.put("/api/user-label-permissions/{permission_id}")
async def update_user_label_permission(
    permission_id: int,
    permission_data: UserLabelPermissionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新用户标签权限"""
    try:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            update_fields = []
            params = []

            if permission_data.can_view is not None:
                update_fields.append("can_view = %s")
                params.append(permission_data.can_view)

            if permission_data.can_create is not None:
                update_fields.append("can_create = %s")
                params.append(permission_data.can_create)

            if permission_data.can_edit is not None:
                update_fields.append("can_edit = %s")
                params.append(permission_data.can_edit)

            if permission_data.can_delete is not None:
                update_fields.append("can_delete = %s")
                params.append(permission_data.can_delete)

            update_fields.append("updated_at = NOW()")
            params.append(permission_id)

            if update_fields:
                sql = f"UPDATE user_label_permissions SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(sql, params)
                conn.commit()

        conn.close()
        return {"message": "用户标签权限更新成功"}
    except Exception as e:
        logger.error(f"更新用户标签权限失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新用户标签权限失败: {str(e)}")

@app.delete("/api/user-label-permissions/{permission_id}")
async def delete_user_label_permission(
    permission_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除用户标签权限"""
    try:
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            sql = "DELETE FROM user_label_permissions WHERE id = %s"
            cursor.execute(sql, (permission_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="权限记录不存在")
            conn.commit()

        conn.close()
        return {"message": "用户标签权限删除成功"}
    except Exception as e:
        logger.error(f"删除用户标签权限失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除用户标签权限失败: {str(e)}")

# ==================== 标签属性管理API ====================

@app.get("/api/label-properties")
async def get_label_properties(
    label_id: Optional[int] = Query(None, description="标签映射ID"),
    current_user: dict = Depends(get_current_user)
):
    """获取标签属性列表"""
    try:
        conn = db_service.get_mysql_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT p.*, l.type, l.neo4j_name, l.display_name as label_display_name
            FROM label_properties p
            JOIN label_mappings l ON p.label_mapping_id = l.id
            """
            params = []
            if label_id:
                sql += " WHERE p.label_mapping_id = %s"
                params.append(label_id)

            sql += " ORDER BY p.label_mapping_id, p.sort_order, p.display_name"
            cursor.execute(sql, params)
            properties = cursor.fetchall()

            # 确保数据类型正确
            for prop in properties:
                # 将 tinyint 转换为布尔值
                prop['is_display'] = bool(prop['is_display'])
                # 确保日期时间格式正确
                if prop.get('created_at'):
                    prop['created_at'] = prop['created_at'].isoformat()
                if prop.get('updated_at'):
                    prop['updated_at'] = prop['updated_at'].isoformat()

        conn.close()
        return properties
    except Exception as e:
        logger.error(f"获取标签属性失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取标签属性失败: {str(e)}")

@app.post("/api/label-properties")
async def create_label_property(
    property_data: LabelPropertyCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建标签属性"""
    try:
        if current_user.get("role") not in ["admin", "editor"]:
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO label_properties (
                label_mapping_id, property_key, display_name, description,
                data_type, sort_order, is_display
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                property_data.label_mapping_id,
                property_data.property_key,
                property_data.display_name,
                property_data.description,
                property_data.data_type,
                property_data.sort_order,
                property_data.is_display
            ))
            property_id = cursor.lastrowid
            conn.commit()

        conn.close()
        return {"message": "标签属性创建成功", "property_id": property_id}
    except Exception as e:
        logger.error(f"创建标签属性失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建标签属性失败: {str(e)}")

@app.put("/api/label-properties/{property_id}")
async def update_label_property(
    property_id: int,
    property_data: LabelPropertyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新标签属性"""
    try:
        if current_user.get("role") not in ["admin", "editor"]:
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            update_fields = []
            params = []

            if property_data.display_name is not None:
                update_fields.append("display_name = %s")
                params.append(property_data.display_name)

            if property_data.description is not None:
                update_fields.append("description = %s")
                params.append(property_data.description)

            if property_data.data_type is not None:
                update_fields.append("data_type = %s")
                params.append(property_data.data_type)

            if property_data.sort_order is not None:
                update_fields.append("sort_order = %s")
                params.append(property_data.sort_order)

            if property_data.is_display is not None:
                update_fields.append("is_display = %s")
                params.append(property_data.is_display)

            update_fields.append("updated_at = NOW()")
            params.append(property_id)

            if update_fields:
                sql = f"UPDATE label_properties SET {', '.join(update_fields)} WHERE id = %s"
                cursor.execute(sql, params)
                conn.commit()

        conn.close()
        return {"message": "标签属性更新成功"}
    except Exception as e:
        logger.error(f"更新标签属性失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新标签属性失败: {str(e)}")

@app.delete("/api/label-properties/{property_id}")
async def delete_label_property(
    property_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除标签属性"""
    try:
        if current_user.get("role") not in ["admin", "editor"]:
            raise HTTPException(status_code=403, detail="权限不足")

        conn = db_service.get_mysql_connection()
        with conn.cursor() as cursor:
            sql = "DELETE FROM label_properties WHERE id = %s"
            cursor.execute(sql, (property_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="标签属性不存在")
            conn.commit()

        conn.close()
        return {"message": "标签属性删除成功"}
    except Exception as e:
        logger.error(f"删除标签属性失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除标签属性失败: {str(e)}")

@app.get("/api/labels/types")
async def get_label_types(current_user: dict = Depends(get_current_user)):
    """获取标签类型列表"""
    try:
        return [
            {"value": "node", "label": "节点标签"},
            {"value": "relationship", "label": "关系标签"}
        ]
    except Exception as e:
        logger.error(f"获取标签类型失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取标签类型失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("neo4j_backend:app", host="0.0.0.0", port=8001, reload=False)