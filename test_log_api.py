#!/usr/bin/env python3
"""
测试日志记录API的简单脚本
"""

import requests
import json

# 配置
API_BASE_URL = "http://localhost:8000/api"
TOKEN = None  # 需要先登录获取token

def test_log_api():
    """测试日志记录API"""

    # 测试数据
    log_data = {
        "user_id": 0,  # 会被后端自动设置
        "user_role": None,  # 会被后端自动设置
        "query_type": "node_query",
        "page_name": "NodeQuery",
        "query_content": "test query",
        "execution_status": "success",
        "result_count": 10,
        "execution_time_ms": 100
    }

    headers = {
        "Content-Type": "application/json"
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    try:
        # 发送请求
        response = requests.post(
            f"{API_BASE_URL}/logs/query",
            headers=headers,
            json=log_data,
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print("✅ 日志记录API测试成功")
        else:
            print("❌ 日志记录API测试失败")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    print("测试日志记录API...")
    test_log_api()