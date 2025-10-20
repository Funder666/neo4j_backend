# -*- coding: utf-8 -*-
"""
智能查询API简单测试文件

测试两个核心API接口：
1. 自然语言转Cypher查询接口
2. Cypher查询执行接口

运行方式：
    python test_intelligent_query_api.py
"""

import requests
import json
import time

# 测试配置
BASE_URL = "http://localhost:8001"
TEST_TIMEOUT = 30

def test_nl_to_cypher():
    """测试自然语言转Cypher查询接口"""
    print("=" * 60)
    print("测试1: 自然语言转Cypher查询接口")
    print("=" * 60)

    url = f"{BASE_URL}/api/intelligent/nl-to-cypher"

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
            response = requests.post(url, json=test_case['request'], timeout=TEST_TIMEOUT)
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
            else:
                print(f"✗ HTTP错误: {response.text}")

        except requests.exceptions.Timeout:
            print("✗ 请求超时")
        except Exception as e:
            print(f"✗ 请求异常: {e}")

    print(f"\n自然语言转Cypher测试完成: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)

def test_execute_cypher():
    """测试Cypher查询执行接口"""
    print("\n" + "=" * 60)
    print("测试2: Cypher查询执行接口")
    print("=" * 60)

    url = f"{BASE_URL}/api/intelligent/execute-cypher"

    # 测试用例
    test_cases = [
        {
            "name": "简单查询 - 限制结果数",
            "request": {
                "cypher": "MATCH (n) RETURN n LIMIT 5",
                "parameters": {},
                "limit": 3
            }
        },
        {
            "name": "参数化查询 - 查找特定标签",
            "request": {
                "cypher": "MATCH (n:Character) RETURN n.name, n.hskLevel LIMIT $limit",
                "parameters": {"limit": 5}
            }
        },
        {
            "name": "复杂查询 - 关系查询(国际中文教育中文水平1级的词语)",
            "request": {
                "cypher": "MATCH (n:Word)-[r:FROM_LEVEL]->(l:InternationalLevel {value: '1'}) RETURN n, r, l LIMIT $limit",
                "limit": 5
            }
        }
    ]

    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print(f"Cypher查询: {test_case['request']['cypher'][:80]}...")

        try:
            start_time = time.time()
            response = requests.post(url, json=test_case['request'], timeout=TEST_TIMEOUT)
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
            else:
                print(f"✗ HTTP错误: {response.text}")

        except requests.exceptions.Timeout:
            print("✗ 请求超时")
        except Exception as e:
            print(f"✗ 请求异常: {e}")

    print(f"\nCypher查询执行测试完成: {success_count}/{len(test_cases)} 成功")
    return success_count == len(test_cases)

def test_health_check():
    """测试健康检查接口"""
    print("\n" + "=" * 60)
    print("测试3: 健康检查接口")
    print("=" * 60)

    url = f"{BASE_URL}/health"

    try:
        response = requests.get(url, timeout=5)
        print(f"HTTP状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"服务状态: {data['status']}")
            print(f"服务名称: {data['service']}")
            print(f"检查时间: {data['timestamp']}")
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

    # 首先检查服务是否运行
    if not test_health_check():
        print("\n服务未运行或无法连接，请先启动服务：")
        print("python intelligent_query_api.py")
        return

    # 执行核心API测试
    test1_result = test_nl_to_cypher()
    test2_result = test_execute_cypher()

    # 总结测试结果
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"自然语言转Cypher接口: {'✓ 通过' if test1_result else '✗ 失败'}")
    print(f"Cypher查询执行接口: {'✓ 通过' if test2_result else '✗ 失败'}")
    print(f"健康检查接口: ✓ 通过")

    if test1_result and test2_result:
        print("\n🎉 所有核心接口测试通过！")
    else:
        print("\n❌ 部分测试失败，请检查服务状态和日志")

if __name__ == "__main__":
    main()