# -*- coding: utf-8 -*-
import requests
import urllib.parse
from neo4j import GraphDatabase

neo4j_config = {
    "uri": "bolt://8.153.207.172:7687",
    "user": "neo4j",
    "password": "xtxzhu2u"
}

def get_idioms_from_neo4j(limit=2):
    driver = GraphDatabase.driver(neo4j_config["uri"], auth=(neo4j_config["user"], neo4j_config["password"]))
    idiom_list = []
    with driver.session() as session:
        query = f"MATCH (n:Idiom) RETURN n.name AS name LIMIT {limit}"
        result = session.run(query)
        for record in result:
            idiom_list.append(record["name"])
    driver.close()
    return idiom_list


def get_chengyu_url(chengyu):
    """
    获取成语详情页面的最终URL
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    }

    search_url = f"https://www.hanyuguoxue.com/chengyu/search?words={urllib.parse.quote(chengyu)}"

    try:
        response = requests.get(search_url, headers=headers, allow_redirects=True, timeout=10)
        return response.url
    except:
        return None


def test_chengyu_crawl():
    """
    测试成语URL获取功能
    """
    test_chengyu_list = get_idioms_from_neo4j(limit=2)

    for chengyu in test_chengyu_list:
        url = get_chengyu_url(chengyu)
        print(f"{chengyu}: {url}")


if __name__ == "__main__":
    test_chengyu_crawl()