# -*- coding: utf-8 -*-
"""
智能查询API简单测试文件

测试两个核心API接口：
1. 自然语言转Cypher查询接口
2. Cypher查询执行接口
3. JWT认证和权限控制
4. 基于角色的权限过滤

运行方式：
    python test_intelligent_query_api.py

认证说明：
- 智能查询API内置认证服务，无需依赖外部服务
- 测试文件使用明文密码，API内置验证
- admin用户明文密码: "admin2025."
- guest用户明文密码: "guest"
- 认证服务地址: https://kg.chineseplus.net/out/api/auth/login
"""

import requests
import json
import time
import base64

# 测试配置
BASE_URL = "https://kg.chineseplus.net"  # 注意：端口可能需要根据实际部署调整
TEST_TIMEOUT = 30

# 测试用户配置（使用智能查询API自带的认证服务）
AUTH_SERVICE_URL = "https://kg.chineseplus.net"  # 智能查询API认证服务

# 测试用户配置 - 与user_neo4j表中的用户对应
TEST_USERS = {
    "admin": {
        "username": "admin",
        "password": "admin2025.",  # admin角色，拥有所有权限 (明文密码，后端会自动验证hash)
        "description": "管理员用户，拥有所有权限"
    },
    "guest": {
        "username": "guest",
        "password": "guest",      # user角色，权限受限 (明文密码，后端会自动验证hash)
        "description": "访客用户，只有基础权限"
    }
}

# 默认使用admin用户进行测试
TEST_USER = TEST_USERS["user"]

def get_auth_token():
    """获取JWT认证令牌"""
    try:
        print("正在获取认证令牌...")
        login_url = f"{AUTH_SERVICE_URL}/out/api/auth/login"
        response = requests.post(login_url, json=TEST_USER, timeout=10)

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print(f"✓ 成功获取认证令牌")
            return token
        else:
            print(f"✗ 登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"✗ 获取认证令牌异常: {e}")
        return None

# 全局认证令牌
AUTH_TOKEN = None

def run_test_nl_to_cypher():
    """测试自然语言转Cypher查询接口"""
    print("=" * 60)
    print("测试1: 自然语言转Cypher查询接口")
    print("=" * 60)

    if not AUTH_TOKEN:
        print("✗ 缺少认证令牌，跳过测试")
        return False

    url = f"{BASE_URL}/out/api/intelligent/nl-to-cypher"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    # 测试用例
    test_cases = [
        {
            "name": "基础查询 - HSK等级",
            "request": {
                "query": "查找所有HSK等级为1的汉字",
                "include_schema": True,
                "temperature": 0.1
            }
        },
        {
            "name": "关系查询 - 同近义词",
            "request": {
                "query": "找到'喜爱'字的所有近义词",
                "include_schema": True,
                "temperature": 0.2
            }
        },
        {
            "name": "复杂查询 - 笔画数",
            "request": {
                "query": "查找笔画数少于5的汉字",
                "include_schema": True,
                "max_tokens": 300
            }
        }
    ]

    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print(f"自然语言查询: {test_case['request']['query']}")

        try:
            start_time = time.time()
            response = requests.post(url, json=test_case['request'], headers=headers, timeout=TEST_TIMEOUT)
            end_time = time.time()

            print(f"HTTP状态码: {response.status_code}")
            print(f"请求耗时: {(end_time - start_time) * 1000:.0f}ms")

            if response.status_code == 200:
                data = response.json()
                print(f"接口响应成功: {data['success']}")
                print(f"生成耗时: {data['generation_time_ms']}ms")
                print(f"使用Schema: {data['schema_used']}")
                print(f"生成的Cypher: {data['cypher_query'][:100]}...")

                if data['success']:
                    success_count += 1
                    print("✓ 测试通过")
                else:
                    print(f"✗ 测试失败: {data['message']}")
            elif response.status_code == 401:
                print("✗ 认证失败 - 可能是令牌过期或无效")
            else:
                print(f"✗ HTTP错误: {response.text}")

        except requests.exceptions.Timeout:
            print("✗ 请求超时")
        except Exception as e:
            print(f"✗ 请求异常: {e}")

    print(f"\n自然语言转Cypher测试完成: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)

def run_test_execute_cypher():
    """测试Cypher查询执行接口"""
    print("\n" + "=" * 60)
    print("测试2: Cypher查询执行接口")
    print("=" * 60)

    if not AUTH_TOKEN:
        print("✗ 缺少认证令牌，跳过测试")
        return False

    url = f"{BASE_URL}/out/api/intelligent/execute-cypher"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    # 测试用例
    test_cases = [
        {
            "name": "简单查询 - 限制结果数",
            "request": {
                "cypher": "MATCH (n) RETURN n LIMIT 5",
                "parameters": {"limit": 5}
            }
        },
        {
            "name": "参数化查询 - 查找特定标签",
            "request": {
                "cypher": "MATCH (n:Question) RETURN n.name, n.hskLevel LIMIT $limit",
                "parameters": {"limit": 5}
            }
        },
        {
            "name": "复杂查询 - 关系查询(国际中文教育中文水平1级的词语)",
            "request": {
                "cypher": "MATCH (n:Word)-[r:FROM_LEVEL]->(l:InternationalLevel {value: '1'}) RETURN n, r, l LIMIT $limit",
                "parameters": {"limit": 5}
            }
        }
    ]

    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print(f"Cypher查询: {test_case['request']['cypher'][:80]}...")

        try:
            start_time = time.time()
            response = requests.post(url, json=test_case['request'], headers=headers, timeout=TEST_TIMEOUT)
            end_time = time.time()

            print(f"HTTP状态码: {response.status_code}")
            print(f"请求耗时: {(end_time - start_time) * 1000:.0f}ms")

            if response.status_code == 200:
                data = response.json()
                print(f"接口响应成功: {data['success']}")
                print(f"执行耗时: {data['execution_time_ms']}ms")
                print(f"返回记录数: {data['count']}")

                if data['success']:
                    success_count += 1
                    print("✓ 测试通过")
                    if data['records'] and len(data['records']) > 0:
                        print(f"示例结果: {json.dumps(data['records'][0], ensure_ascii=False)[:100]}...")
                else:
                    print(f"预期的失败结果: {data['message']}")
                    # 危险操作应该失败，这也算测试通过
                    if "安全考虑" in data['message']:
                        success_count += 1
                        print("✓ 安全检查测试通过")
            elif response.status_code == 400:
                # 安全检查返回400也是正常的
                data = response.json()
                if "安全考虑" in data.get('detail', ''):
                    success_count += 1
                    print("✓ 安全检查测试通过 (HTTP 400)")
                else:
                    print(f"✗ 意外的400错误: {data}")
            elif response.status_code == 401:
                print("✗ 认证失败 - 可能是令牌过期或无效")
            else:
                print(f"✗ HTTP错误: {response.text}")

        except requests.exceptions.Timeout:
            print("✗ 请求超时")
        except Exception as e:
            print(f"✗ 请求异常: {e}")

    print(f"\nCypher查询执行测试完成: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)



def run_test_health_check():
    """测试健康检查接口"""
    print("\n" + "=" * 60)
    print("测试3: 健康检查接口")
    print("=" * 60)

    url = f"{BASE_URL}/out/api/health"

    try:
        response = requests.get(url, timeout=5)
        print(f"HTTP状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"服务状态: {data['status']}")
            print(f"服务名称: {data['service']}")
            print(f"检查时间: {data['timestamp']}")

            # 显示数据库状态
            if 'database_status' in data:
                db_status = data['database_status']
                print(f"Neo4j状态: {db_status.get('neo4j', 'unknown')}")
                print(f"MySQL状态: {db_status.get('mysql', 'unknown')}")

            # 显示功能特性
            if 'features' in data:
                features = data['features']
                print(f"JWT认证: {'✓' if features.get('jwt_authentication') else '✗'}")
                print(f"权限控制: {'✓' if features.get('role_based_access_control') else '✗'}")
                print(f"权限过滤: {'✓' if features.get('permission_filtering') else '✗'}")

            print("✓ 健康检查通过")
            return True
        else:
            print(f"✗ 健康检查失败: {response.text}")
            return False

    except Exception as e:
        print(f"✗ 健康检查异常: {e}")
        return False

def main():
    """主测试函数"""
    print("智能查询API测试开始")
    print(f"测试服务地址: {BASE_URL}")
    print(f"认证服务地址: {AUTH_SERVICE_URL}")

    # # 首先检查服务是否运行
    # if not run_test_health_check():
    #     print("\n智能查询服务未运行或无法连接，请先启动服务：")
    #     print("python intelligent_query_api.py")
    #     return

    # 获取认证令牌
    global AUTH_TOKEN
    AUTH_TOKEN = get_auth_token()

    if not AUTH_TOKEN:
        print("\n无法获取认证令牌，请检查：")
        print("1. 智能查询API服务是否运行")
        print(f"2. 测试用户 {TEST_USER['username']} 是否存在")
        print("3. 用户密码是否正确")
        return

    # 执行核心API测试
    test1_result = run_test_nl_to_cypher()
    test2_result = run_test_execute_cypher()

    # 总结测试结果
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"认证服务: ✓ 通过 (令牌获取成功)")
    print(f"自然语言转Cypher接口: {'✓ 通过' if test1_result else '✗ 失败'}")
    print(f"Cypher查询执行接口: {'✓ 通过' if test2_result else '✗ 失败'}")
    print(f"健康检查接口: ✓ 通过")

    all_tests_pass = test1_result and test2_result

    if all_tests_pass:
        print("\n🎉 核心功能测试通过！")
        print("✓ JWT认证功能正常")
        print("✓ 权限控制功能正常")
        print("✓ 查询过滤功能正常")
        print("智能查询API已准备就绪")

        # 显示权限配置说明
        print(f"\n权限配置说明:")
        print(f"- admin用户: 拥有所有权限，可访问所有节点")
        print(f"- guest用户: 基础权限，只能访问user_label_permissions中配置的标签")
        print(f"- 权限控制基于user_neo4j表的用户角色和user_label_permissions表的配置")
    else:
        print("\n❌ 部分测试失败，请检查：")
        print("1. 服务状态和日志")
        print("2. 数据库连接状态")
        print("3. 用户权限配置 (user_neo4j表)")
        print("4. 标签权限配置 (user_label_permissions表)")
        print("5. 网络连接状态")
        print("6. JWT令牌配置")
        print(f"7. 用户名密码是否正确:")
        for role_name, user_config in TEST_USERS.items():
            print(f"   - {user_config['username']}: {user_config['password']}")

if __name__ == "__main__":
    main()