# -*- coding: utf-8 -*-
import requests
import urllib.parse


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
    test_chengyu_list = [
        "一心一意",
        "画龙点睛",
        "守株待兔"
    ]

    for chengyu in test_chengyu_list:
        url = get_chengyu_url(chengyu)
        print(f"{chengyu}: {url}")


if __name__ == "__main__":
    test_chengyu_crawl()