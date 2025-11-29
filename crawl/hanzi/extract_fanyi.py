import re
import json
from bs4 import BeautifulSoup


def extract_fanyi_from_url(url):
    """
    从URL获取HTML并提取翻译信息，返回JSON格式数据
    针对data-id="翻译"板块进行解析
    """
    import requests
    import time

    # 获取HTML，加headers和延时
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html_content = response.text
    time.sleep(1)  # 延时1s

    return extract_fanyi_from_html(html_content)


def extract_fanyi_from_html(html_content):
    """
    从HTML内容中提取翻译信息（不访问URL）
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 定位到 data-id="翻译" 的div
    fanyi_div = soup.find('div', {'data-id': '翻译'})
    if not fanyi_div:
        return {"error": "未找到翻译板块"}

    result = {
        "fanyiTitle": "翻译",
        "data": {}
    }

    # 提取翻译标题
    header_h2 = fanyi_div.find('h2')
    if header_h2:
        result["data"]["title"] = header_h2.get_text().strip()

    # 定位到内容主体
    content_body = fanyi_div.find('div', class_='content-card-body')
    if content_body:
        # 查找翻译列表
        fanyi_ol = content_body.find('ol', class_='zi-fanyi')
        if fanyi_ol:
            translations = extract_translations(fanyi_ol)
            result["data"]["translations"] = translations

    return result


def extract_translations(ol_element):
    """
    从ol.zi-fanyi元素中提取所有翻译条目
    """
    translations = []

    # 查找所有li元素
    li_elements = ol_element.find_all('li')

    for li in li_elements:
        translation_item = extract_single_translation(li)
        if translation_item:
            translations.append(translation_item)

    return translations


def extract_single_translation(li_element):
    """
    提取单个翻译条目
    """
    # 查找语言标签
    label = li_element.find('label', class_='badge')
    if not label:
        return None

    # 提取语言名称
    language = label.get_text().strip()

    # 移除label元素，获取纯翻译内容
    if label:
        label.decompose()

    # 提取翻译文本
    translation_text = li_element.get_text().strip()

    # 清理多余的空白字符
    translation_text = re.sub(r'\s+', ' ', translation_text)

    translation_item = {
        "language": language,
        "translation": translation_text
    }

    return translation_item


def test_extract_fanyi():
    """
    测试翻译信息提取功能
    """
    # 测试HTML片段
    test_html = '''<div class="card" data-id="翻译"><div class="content-card" style="position: relative;"><div class="sticky-events--sentinel sticky-events--sentinel-top" style="left: 0px; position: relative; right: 0px; visibility: hidden; top: calc(-51px);"></div><div class="content-card-header outer" style="position: sticky;"><h2 id="fanyi">王字的翻译</h2><a class="font-sm" data-feedback="" data-label="#翻译"><i class="iconfont icon-help2"></i> 纠错</a></div><div class="content-card-body show" id="fy"><ol class="zi-fanyi"><li><label class="badge badge-info">英语</label> king, ruler; royal; surname</li><li><label class="badge badge-info">德语</label> Radikal Nr. 96 , König (S)</li><li><label class="badge badge-info">法语</label> roi, prince, (nom de famille)​, régner sur</li></ol></div><div class="sticky-events--sentinel sticky-events--sentinel-bottom" style="left: 0px; position: relative; right: 0px; visibility: hidden; bottom: 51px; height: 38px;"></div></div></div>'''

    # 提取翻译信息
    fanyi_data = extract_fanyi_from_html(test_html)

    print("翻译信息提取测试：")
    print("=" * 60)
    print(json.dumps(fanyi_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_extract_fanyi()