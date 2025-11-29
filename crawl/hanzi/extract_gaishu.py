import re
import json
from bs4 import BeautifulSoup


def extract_gaishu_from_url(url):
    """
    从URL获取HTML并提取概述信息，返回JSON格式数据
    针对data-id="概述"板块进行解析
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

    soup = BeautifulSoup(html_content, 'html.parser')

    # 定位到 data-id="概述" 的div
    gaishu_div = soup.find('div', {'data-id': '概述'})
    if not gaishu_div:
        return {"error": "未找到概述板块"}

    result = {
        "gaishuTitle": "概述",
        "data": {}
    }

    # 提取概述标题
    header_h2 = gaishu_div.find('h2')
    if header_h2:
        result["data"]["title"] = header_h2.get_text().strip()

    # 定位到内容主体
    content_body = gaishu_div.find('div', class_='content-card-body')
    if content_body:
        summary_div = content_body.find('div', class_='zi-summary')
        if summary_div:
            # 提取所有段落
            paragraphs = summary_div.find_all('p')
            summary_info = []

            for p in paragraphs:
                p_text = p.get_text().strip()
                if p_text:
                    # 分析每个段落的内容类型
                    paragraph_data = analyze_paragraph(p_text)
                    if paragraph_data:
                        summary_info.append(paragraph_data)

            result["data"]["summary_info"] = summary_info

    return result


def analyze_paragraph(paragraph_text):
    """
    分析概述段落，只保留原始文本
    """
    # 只保留原始文本，不需要提取其他字段
    return {
        "full_text": paragraph_text
    }


def extract_gaishu_from_html(html_content):
    """
    从HTML内容中提取概述信息（不访问URL）
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 定位到 data-id="概述" 的div
    gaishu_div = soup.find('div', {'data-id': '概述'})
    if not gaishu_div:
        return {"error": "未找到概述板块"}

    result = {
        "gaishuTitle": "概述",
        "data": {}
    }

    # 提取概述标题
    header_h2 = gaishu_div.find('h2')
    if header_h2:
        result["data"]["title"] = header_h2.get_text().strip()

    # 定位到内容主体
    content_body = gaishu_div.find('div', class_='content-card-body')
    if content_body:
        summary_div = content_body.find('div', class_='zi-summary')
        if summary_div:
            # 提取所有段落
            paragraphs = summary_div.find_all('p')
            summary_info = []

            for p in paragraphs:
                p_text = p.get_text().strip()
                if p_text:
                    # 分析每个段落的内容类型
                    paragraph_data = analyze_paragraph(p_text)
                    if paragraph_data:
                        summary_info.append(paragraph_data)

            result["data"]["summary_info"] = summary_info

    return result


def test_extract_gaishu():
    """
    测试概述信息提取功能
    """
    # 测试HTML片段
    test_html = '''<div class="card" data-id="概述"><div class="content-card" style="position: relative;"><div class="sticky-events--sentinel sticky-events--sentinel-top" style="left: 0px; position: relative; right: 0px; visibility: hidden; top: calc(-51px);"></div><div class="content-card-header outer" style="position: sticky;"><h2 id="gaishu">王字概述</h2><a class="font-sm" data-feedback="" data-label="#概述"><i class="iconfont icon-help2"></i> 纠错</a></div><div class="content-card-body show" id="gs"><div class="zi-summary show-more-container open"><p>〔王〕字是多音字，拼音是（wáng、wàng），部首是<em>王部</em>，总笔画是<em>4画</em>，是独体字。</p><p>〔王〕字是独体字，五行属土。</p><p>〔王〕字造字法是象形字。王字的甲骨文为斧钺之形，斧钺为礼器，象征王者之权威。本义是天子、君主。</p><p>〔王〕字仓颉码是<em>MG</em>，五笔是<em>GGGG</em>，四角号码是<em>10104</em>，郑码是<em>CA</em>，中文电码是<em>3769</em>，区位码是<em>4585</em>。</p><p>〔王〕字的UNICODE是<em>U+738B</em>，位于UNICODE的<em>中日韩统一表意文字 (基本汉字)</em>，10进制： 29579，UTF-32：0000738B，UTF-8：E7 8E 8B。</p><p>〔王〕字在<em>《通用规范汉字表》</em>的<em>一级字表</em>中，序号<em>0075</em>，属<em>常用字</em>。</p><p>〔王〕字异体字是<em><a class="primary" href="/zidian/zi-29577"><span class="zi-font">玉</span></a>、<a class="primary" href="/zidian/zi-132731"><span class="zi-font">𠙻</span></a>、<a class="primary" href="/zidian/zi-134198"><span class="zi-font">𠰶</span></a>、<a class="primary" href="/zidian/zi-138084"><span class="zi-font">𡭤</span></a>、<a class="primary" href="/zidian/zi-149767"><span class="zi-font">𤤇</span></a>、<a class="primary" href="/zidian/zi-153421"><span class="zi-font">𥝍</span></a></em>。</p><div class="show-more-toggle"><button class="btn btn-outline-danger btn-round">展开更多 <i class="iconfont icon-arrow-down"></i></button></div></div></div><div class="sticky-events--sentinel sticky-events--sentinel-bottom" style="left: 0px; position: absolute; right: 0px; visibility: hidden; bottom: 51px; height: 38px;"></div></div></div>'''

    # 提取概述信息
    gaishu_data = extract_gaishu_from_html(test_html)

    print("概述信息提取测试：")
    print("=" * 60)
    print(json.dumps(gaishu_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_extract_gaishu()