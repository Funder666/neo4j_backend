#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from passlib.context import CryptContext

# 创建密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 生成密码hash
admin_password = "admin2025."
neo4j_password = "guest"

admin_hash = pwd_context.hash(admin_password)
neo4j_hash = pwd_context.hash(neo4j_password)

print("=== 密码Hash生成结果 ===")
print(f"admin用户密码 '{admin_password}' 的hash:")
print(admin_hash)
print()
print(f"neo4j用户密码 '{neo4j_password}' 的hash:")
print(neo4j_hash)
print()

# 验证测试
print("=== 验证测试 ===")
print(f"admin密码验证: {pwd_context.verify(admin_password, admin_hash)}")
print(f"neo4j密码验证: {pwd_context.verify(neo4j_password, neo4j_hash)}")
print()

# 生成SQL更新语句
print("=== SQL更新语句 ===")
print("UPDATE user_neo4j SET password_hash = %s WHERE username = 'admin';")
print(f"参数: {admin_hash}")
print()
print("UPDATE user_neo4j SET password_hash = %s WHERE username = 'neo4j';")
print(f"参数: {neo4j_hash}")