import requests
import json

content = input("请输入要查询的内容：")
# content = "办法{}Context(100)"
# content = "办法{}Freq(100)"


def query_post(query):
    url = "https://corpus.chineseplus.net/corpus/api/v1/search/0/corpus"
    data = {"query": query}
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    try:
        response = requests.post(url, json=data, headers=headers)
        print("状态码:", response.status_code)
        # print("检索类型:", response.json()["data"]["Type"])
        # print("检索返回数量:", response.json()["data"]["total"])
        print("返回数据:", response.json()["data"])
    except requests.exceptions.RequestException as e:
        print("请求错误:", e)
    except json.JSONDecodeError as e:
        print("JSON解析错误:", e)


query_post(content)
