import re
import json
import requests
import time  # 延时防封
import pymysql
from bs4 import BeautifulSoup

# 数据库配置
mysql_config = {
    "host": "8.153.207.172",
    "user": "root",
    "password": "Restart1128",
    "database": "lab_education",
    "port": 3307
}


def extract_character_from_url(url):
    """从URL提取Unicode decimal"""
    match = re.search(r'zi-(\d+)', url)
    return int(match.group(1)) if match else None


def extract_basic_info_from_url(url):
    """
    从URL获取HTML并提取基本信息，返回JSON格式数据
    针对data-id="基本信息"板块进行解析
    """
    # 获取HTML，加headers和延时
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html_content = response.text
    # time.sleep(1)  # 延时1s

    soup = BeautifulSoup(html_content, 'html.parser')

    # 定位到 data-id="基本信息" 的div
    basic_info_div = soup.find('div', {'data-id': '基本信息'})
    if not basic_info_div:
        return {"error": "未找到基本信息板块"}

    # 定位到 zi-title div
    zi_title_div = basic_info_div.find('div', class_='zi-title')
    if not zi_title_div:
        return {"error": "未找到zi-title板块"}

    result = {
        "baseInfoTitle": "基本信息",
        "data": {}
    }

    # 1. 提取汉字
    character_element = zi_title_div.find('h2')
    if character_element:
        result["data"]['character'] = character_element.get_text().strip()

    # 2. 提取拼音信息
    pinyin_div = zi_title_div.find('div', class_='pinyin')
    if pinyin_div:
        pinyin_info = []
        voice_spans = pinyin_div.find_all('span', class_='voice')
        for voice_span in voice_spans:
            py_em = voice_span.find('em', class_='py')
            zy_em = voice_span.find('em', class_='zy')
            voice_data = voice_span.get('data-voice', '')

            pinyin_entry = {
                'pinyin': py_em.get_text().strip() if py_em else '',
                'zhuyin': zy_em.get_text().strip() if zy_em else '',
                'audio_file': voice_data
            }
            pinyin_info.append(pinyin_entry)
        result["data"]['pinyin_info'] = pinyin_info

    # 3. 提取基本信息（部首、笔画等）
    zi_title_extra = zi_title_div.find('div', class_='zi-title-extra')
    if zi_title_extra:
        spans = zi_title_extra.find_all('span')
        for span in spans:
            text = span.get_text().strip()
            if '部' in text and not text.endswith('部'):
                result["data"]['bushou'] = text
            elif '画' in text and '共' in text:
                result["data"]['bihua_count'] = text
            elif '独体字' in text or '左右结构' in text or '上下结构' in text:
                result["data"]['character_type'] = text
            elif 'U+' in text:
                result["data"]['unicode_basic'] = text
            elif 'CJK' in text:
                result["data"]['character_set'] = text

    # 4. 提取标签
    zi_tags = zi_title_div.find('div', class_='zi-tags')
    if zi_tags:
        tags = []
        badge_links = zi_tags.find_all('a', class_='badge')
        for link in badge_links:
            tags.append(link.get_text().strip())
        result["data"]['tags'] = tags

    # 5. 提取分类
    zi_category = zi_title_div.find('div', class_='zi-category')
    if zi_category:
        result["data"]['category'] = zi_category.get_text().strip()

    # 6. 提取详细属性信息
    zi_attrs = basic_info_div.find('div', class_='zi-attrs')
    if zi_attrs:
        attrs_list = zi_attrs.find('div', class_='zi-attrs-list')
        if attrs_list:
            paragraphs = attrs_list.find_all('p')
            for p in paragraphs:
                label = p.find('label')
                if label:
                    label_text = label.get_text().strip()
                    span = p.find('span')
                    if span:
                        value_text = span.get_text().strip()

                        # 映射标签到对应字段
                        if label_text == '部首':
                            # 提取链接信息
                            link = span.find('a')
                            result["data"]['bushou_detail'] = {
                                'text': value_text,
                                'link': link.get('href', '') if link else ''
                            }
                        elif label_text == '总笔画':
                            link = span.find('a')
                            result["data"]['total_strokes'] = {
                                'text': value_text,
                                'link': link.get('href', '') if link else ''
                            }
                        elif label_text == '结构':
                            result["data"]['structure'] = value_text
                        elif label_text == '造字法':
                            result["data"]['formation_method'] = value_text
                        elif label_text == '五行':
                            result["data"]['five_elements'] = value_text
                        elif label_text == '五笔':
                            result["data"]['wubi'] = value_text
                        elif label_text == '仓颉':
                            result["data"]['cangjie'] = value_text
                        elif label_text == '郑码':
                            result["data"]['zhengma'] = value_text
                        elif label_text == '四角':
                            result["data"]['sijiaohaoma'] = value_text
                        elif label_text == '中文电码':
                            result["data"]['telegraph_code'] = value_text
                        elif label_text == '区位码':
                            result["data"]['zone_code'] = value_text
                        elif label_text == '统一码':
                            result["data"]['unicode_full'] = value_text
                        elif label_text == '笔画':
                            # 提取笔画顺序
                            em_tags = span.find_all('em')
                            if len(em_tags) >= 2:
                                result["data"]['stroke_order'] = {
                                    'code': em_tags[0].get_text().strip(),
                                    'description': em_tags[1].get_text().strip()
                                }
                        elif label_text == '异体字':
                            # 提取异体字链接
                            variant_chars = []
                            links = span.find_all('a')
                            for link in links:
                                char = link.get_text().strip()
                                if char:
                                    variant_chars.append({
                                        'character': char,
                                        'url': link.get('href', '')
                                    })
                            result["data"]['variant_characters'] = variant_chars

    return result


def extract_evolution_data(url):
    """
    通用的提取函数：直接定位 zi-zyxc div，解析 <p> 条目。
    支持有/无引号 HTML（韩/王差异）。
    """
    # 获取HTML，加headers和延时
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html_content = response.text
    # time.sleep(1)  # 延时1s

    # 提取 unicode_decimal
    unicode_decimal = extract_character_from_url(url)

    # 提取 character 从 h2（支持无引号 id=zyzx）
    h2_pattern = r'<h2 id\s*=\s*(["\']?)zyzx\1\s*>([^<]+?)的字源字形</h2>'
    h2_match = re.search(h2_pattern, html_content)
    character = h2_match.group(2).strip() if h2_match else '未知'

    # 直接定位 zi-zyxc div（支持有/无引号）
    zyxc_pattern = r'<div\s+class\s*=\s*(["\']?)zi-zyxc\1\s*>(.*?)</div>'
    zyxc_match = re.search(zyxc_pattern, html_content, re.DOTALL)
    if not zyxc_match:
        raise ValueError("未找到 zi-zyxc 板块")
    p_html = zyxc_match.group(2)

    # 提取所有 p
    p_pattern = r'<p>(.*?)</p>'
    p_blocks = re.findall(p_pattern, p_html, re.DOTALL)

    evolution_data = []

    for block in p_blocks:
        # alt: 支持有/无引号，停止于下一个属性
        alt_match = re.search(r'alt\s*=\s*(["\']?)([^"\']+?)\1(?=\s+(class|data-src|src)|>)', block)
        alt = alt_match.group(2).strip() if alt_match else ''

        # image_url: 优先 src（有/无引号），否则 data-src
        src_match = re.search(r'src\s*=\s*(["\']?)([^"\'>]+?)\1(?=\s+[^=]|>)', block)
        src = src_match.group(2).strip() if src_match else ''

        data_src_match = re.search(r'data-src\s*=\s*(["\']?)([^"\'>]+?)\1(?=\s+[^=]|>)', block)
        data_src = data_src_match.group(2).strip() if data_src_match else ''

        image_url = src if src else data_src
        if not image_url:
            continue

        # period: 支持有/无引号
        period_match = re.search(r'<span\s+class\s*=\s*(["\']?)period\1\s*>([^<]*)</span>', block)
        period = period_match.group(2).strip() if period_match else ''

        # style
        style_match = re.search(r'<span\s+class\s*=\s*(["\']?)style\1\s*>([^<]*)</span>', block)
        style = style_match.group(2).strip() if style_match else ''

        # source
        source_match = re.search(r'<span\s+class\s*=\s*(["\']?)source\1\s*>([^<]*)</span>', block)
        source = source_match.group(2).strip() if source_match else ''

        evolution_data.append({
            "character": character,
            "image_url": image_url,
            "alt": alt,
            "period": period,
            "style": style,
            "source": source
        })

    return evolution_data


def extract_gaishu_from_url(url):
    """
    从URL获取HTML并提取概述信息，返回JSON格式数据
    针对data-id="概述"板块进行解析
    """
    # 获取HTML，加headers和延时
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html_content = response.text
    # time.sleep(1)  # 延时1s

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
                    paragraph_data = analyze_gaishu_paragraph(p_text)
                    if paragraph_data:
                        summary_info.append(paragraph_data)

            result["data"]["summary_info"] = summary_info

    return result


def analyze_gaishu_paragraph(paragraph_text):
    """
    分析概述段落，只保留原始文本
    """
    # 只保留原始文本，不需要提取其他字段
    return {
        "full_text": paragraph_text
    }


def extract_yisi_from_url(url):
    """
    从URL获取HTML并提取意思信息，返回JSON格式数据
    针对data-id="意思"板块进行解析
    """
    # 获取HTML，加headers和延时
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html_content = response.text
    # time.sleep(1)  # 延时1s

    soup = BeautifulSoup(html_content, 'html.parser')

    # 定位到 data-id="意思" 的div
    yisi_div = soup.find('div', {'data-id': '意思'})
    if not yisi_div:
        return {"error": "未找到意思板块"}

    result = {
        "yisiTitle": "意思",
        "data": {}
    }

    # 提取意思标题
    header_h2 = yisi_div.find('h2')
    if header_h2:
        result["data"]["title"] = header_h2.get_text().strip()

    # 详细提取：包括基本解释和详细解释的结构化信息
    content_body = yisi_div.find('div', class_='content-card-body')
    if content_body:
        all_explanations = []

        zi_contents = content_body.find_all('div', class_='zi-content')

        for zi_content in zi_contents:
            zi_content_data = extract_zi_content(zi_content)
            if zi_content_data:
                all_explanations.append(zi_content_data)

        result["data"]["explanations"] = all_explanations

    return result


def extract_zi_content(zi_content_div):
    """
    提取单个zi-content的内容，包括基本解释和详细解释
    """
    zi_content_data = {
        "basic_explanation": [],
        "detailed_explanation": []
    }

    # 提取汉字标题和拼音
    main_heading = zi_content_div.find('div', class_='zi-heading main')
    if main_heading:
        character_h3 = main_heading.find('h3')
        if character_h3:
            zi_content_data["character"] = character_h3.get_text().strip()

        voice_span = main_heading.find('span', class_='voice')
        if voice_span:
            py_em = voice_span.find('em', class_='py')
            zy_em = voice_span.find('em', class_='zy')
            voice_data = voice_span.get('data-voice', '')

            zi_content_data["pinyin_info"] = {
                'pinyin': py_em.get_text().strip() if py_em else '',
                'zhuyin': zy_em.get_text().strip() if zy_em else '',
                'audio_file': voice_data
            }

    # 提取基本解释
    basic_explain = zi_content_div.find('div', class_='zi-basic-explain')
    if basic_explain:
        for p in basic_explain.find_all('p', class_='explain'):
            basic_item = extract_explain_paragraph(p)
            if basic_item:
                zi_content_data["basic_explanation"].append(basic_item)

    # 提取详细解释
    detail_explain = zi_content_div.find('div', class_='zi-detail-explain')
    if detail_explain:
        current_cixing = ""

        # 遍历所有子元素
        for element in detail_explain.children:
            if element.name == 'p' and 'cixing' in element.get('class', []):
                # 词性标记
                current_cixing = element.get_text().strip()
            elif element.name == 'p' and 'explain' in element.get('class', []):
                # 解释条目
                detail_item = extract_detailed_explain_paragraph(element, current_cixing)
                if detail_item:
                    zi_content_data["detailed_explanation"].append(detail_item)

    return zi_content_data


def extract_explain_paragraph(p_element):
    """
    提取基本解释段落
    """
    no_span = p_element.find('span', class_='no')
    text_span = p_element.find('span', class_='text')
    eg_span = p_element.find('span', class_='eg')

    return {
        "number": no_span.get_text().strip() if no_span else "",
        "explanation": text_span.get_text().strip() if text_span else "",
        "example": eg_span.get_text().strip() if eg_span else "",
        "full_text": p_element.get_text().strip()
    }


def extract_detailed_explain_paragraph(p_element, current_cixing):
    """
    提取详细解释段落，包括引证、例子、英文等额外信息
    """
    no_span = p_element.find('span', class_='no')

    detail_item = {
        "cixing": current_cixing,
        "number": no_span.get_text().strip() if no_span else "",
        "content": p_element.get_text().strip(),
        "quotes": [],
        "examples": [],
        "english": []
    }

    # 获取父级 zi-detail-explain 容器
    zi_detail_explain = p_element.find_parent('div', class_='zi-detail-explain')
    if zi_detail_explain:
        # 找到所有的explain段落，记录当前explain的位置
        all_explains = zi_detail_explain.find_all('p', class_='explain')
        current_explain_index = None

        for i, explain in enumerate(all_explains):
            if explain == p_element:  # 直接比较对象引用
                current_explain_index = i
                break

        # 如果找到了当前explain的位置
        if current_explain_index is not None:
            # 找到所有的extra元素
            extra_elements = zi_detail_explain.find_all('p', class_='extra')

            # 为当前explain分组对应的extra元素
            extra_groups = {}
            current_group = []

            for extra in extra_elements:
                # 找到extra前面最近的explain
                prev_explain = None
                prev_sibling = extra.previous_sibling

                while prev_sibling:
                    if (hasattr(prev_sibling, 'name') and
                        prev_sibling.name == 'p' and
                        'explain' in prev_sibling.get('class', [])):
                        prev_explain = prev_sibling
                        break
                    prev_sibling = prev_sibling.previous_sibling

                # 如果这个extra前面有explain，就分组
                if prev_explain:
                    for i, explain in enumerate(all_explains):
                        if explain == prev_explain:
                            if i not in extra_groups:
                                extra_groups[i] = []
                            extra_groups[i].append(extra)
                            break

            # 获取当前explain对应的extra元素
            if current_explain_index in extra_groups:
                for extra in extra_groups[current_explain_index]:
                    # 提取内容
                    content_span = extra.find('span')
                    content = content_span.get_text().strip() if content_span else ""

                    # 根据类名确定内容类型
                    classes = extra.get('class', [])
                    if 'quotes' in classes:
                        detail_item["quotes"] = content
                    elif 'eg' in classes:
                        detail_item["examples"] = content
                    elif 'en' in classes:
                        detail_item["english"] = content

    return detail_item


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
    # time.sleep(1)  # 延时1s

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
    import re
    translation_text = re.sub(r'\s+', ' ', translation_text)

    translation_item = {
        "language": language,
        "translation": translation_text
    }

    return translation_item


def extract_guoyu_from_url(url):
    """
    从URL获取HTML并提取国语辞典信息，返回JSON格式数据
    针对data-id="国语辞典"板块进行解析
    """
    import requests
    import time

    # 获取HTML，加headers和延时
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html_content = response.text
    # time.sleep(1)  # 延时1s

    soup = BeautifulSoup(html_content, 'html.parser')

    # 定位到 data-id="国语辞典" 的div
    guoyu_div = soup.find('div', {'data-id': '国语辞典'})
    if not guoyu_div:
        return {"error": "未找到国语辞典板块"}

    result = {
        "guoyuTitle": "国语辞典",
        "data": {}
    }

    # 提取标题
    header_h2 = guoyu_div.find('h2')
    if header_h2:
        result["data"]["title"] = header_h2.get_text().strip()

    # 定位到内容主体
    content_body = guoyu_div.find('div', class_='content-card-body')
    if content_body:
        # 提取主要内容
        zi_contents = content_body.find('div', class_='zi-contents')
        if zi_contents:
            main_content = extract_guoyu_main_content(zi_contents)
            if main_content:
                result["data"]["main_content"] = main_content

        # 提取注释说明
        zi_notes = content_body.find('div', class_='zi-notes')
        if zi_notes:
            result["data"]["notes"] = zi_notes.get_text().strip()

    return result


def extract_guoyu_main_content(zi_contents_div):
    """
    提取国语辞典的主要内容（汉字信息和详细解释）
    """
    # 查找所有 zi-content
    zi_contents = zi_contents_div.find_all('div', class_='zi-content')

    all_contents = []

    for zi_content in zi_contents:
        content_data = extract_guoyu_single_zi_content(zi_content)
        if content_data:
            all_contents.append(content_data)

    return all_contents


def extract_guoyu_single_zi_content(zi_content_div):
    """
    提取国语辞典单个 zi-content 的内容
    """
    content_data = {}

    # 提取汉字标题和拼音信息
    main_heading = zi_content_div.find('div', class_='zi-heading main')
    if main_heading:
        # 提取汉字
        character_h3 = main_heading.find('h3')
        if character_h3:
            content_data["character"] = character_h3.get_text().strip()

        # 提取拼音信息
        voice_span = main_heading.find('span', class_='voice')
        if voice_span:
            pinyin_info = extract_guoyu_pinyin_info(voice_span)
            content_data["pinyin_info"] = pinyin_info

    # 提取详细解释
    detail_explain_div = zi_content_div.find('div', class_='zi-detail-explain')
    if detail_explain_div:
        explanations = extract_guoyu_detailed_explanations(detail_explain_div)
        content_data["detailed_explanations"] = explanations

    return content_data if content_data else None


def extract_guoyu_pinyin_info(voice_span):
    """
    提取国语辞典的拼音信息
    """
    py_em = voice_span.find('em', class_='py')
    zy_em = voice_span.find('em', class_='zy')
    voice_data = voice_span.get('data-voice', '')

    return {
        'pinyin': py_em.get_text().strip() if py_em else '',
        'zhuyin': zy_em.get_text().strip() if zy_em else '',
        'audio_file': voice_data
    }


def extract_guoyu_detailed_explanations(detail_explain_div):
    """
    提取国语辞典的详细解释，按词性分组
    """
    explanations = []

    # 获取所有元素，按词性分组
    all_elements = detail_explain_div.find_all(['p'], recursive=False)

    current_cixing = ""

    for element in all_elements:
        if 'cixing' in element.get('class', []):
            # 词性标记
            current_cixing = element.get_text().strip()
        elif 'explain' in element.get('class', []):
            # 解释条目 - 使用与意思板块相同的修复逻辑
            detail_item = extract_guoyu_explain_paragraph(element, current_cixing)
            if detail_item:
                explanations.append(detail_item)

    return explanations


def extract_guoyu_explain_paragraph(p_element, current_cixing):
    """
    提取国语辞典的解释段落，包括引证、例子等额外信息
    使用与意思板块相同的修复逻辑来处理extra元素
    """
    no_span = p_element.find('span', class_='no')

    detail_item = {
        "cixing": current_cixing,
        "number": no_span.get_text().strip() if no_span else "",
        "content": p_element.get_text().strip(),
        "quotes": [],
        "examples": []
    }

    # 获取父级 zi-detail-explain 容器
    zi_detail_explain = p_element.find_parent('div', class_='zi-detail-explain')
    if zi_detail_explain:
        # 找到所有的explain段落，记录当前explain的位置
        all_explains = zi_detail_explain.find_all('p', class_='explain')
        current_explain_index = None

        for i, explain in enumerate(all_explains):
            if explain == p_element:  # 直接比较对象引用
                current_explain_index = i
                break

        # 如果找到了当前explain的位置
        if current_explain_index is not None:
            # 找到所有的extra元素
            extra_elements = zi_detail_explain.find_all('p', class_='extra')

            # 为当前explain分组对应的extra元素
            extra_groups = {}

            for extra in extra_elements:
                # 找到extra前面最近的explain
                prev_explain = None
                prev_sibling = extra.previous_sibling

                while prev_sibling:
                    if (hasattr(prev_sibling, 'name') and
                        prev_sibling.name == 'p' and
                        'explain' in prev_sibling.get('class', [])):
                        prev_explain = prev_sibling
                        break
                    prev_sibling = prev_sibling.previous_sibling

                # 如果这个extra前面有explain，就分组
                if prev_explain:
                    for i, explain in enumerate(all_explains):
                        if explain == prev_explain:
                            if i not in extra_groups:
                                extra_groups[i] = []
                            extra_groups[i].append(extra)
                            break

            # 获取当前explain对应的extra元素
            if current_explain_index in extra_groups:
                for extra in extra_groups[current_explain_index]:
                    # 提取内容
                    content_span = extra.find('span')
                    content = content_span.get_text().strip() if content_span else ""

                    # 根据类名确定内容类型
                    classes = extra.get('class', [])
                    if 'quotes' in classes:
                        detail_item["quotes"] = content
                    elif 'eg' in classes:
                        detail_item["examples"] = content

    return detail_item


def extract_liangan_from_url(url):
    """
    从URL获取HTML并提取两岸词典信息，返回JSON格式数据
    针对data-id="两岸词典"板块进行解析
    """
    import requests
    import time

    # 获取HTML，加headers和延时
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html_content = response.text
    # time.sleep(1)  # 延时1s

    soup = BeautifulSoup(html_content, 'html.parser')

    # 定位到 data-id="两岸词典" 的div
    liangan_div = soup.find('div', {'data-id': '两岸词典'})
    if not liangan_div:
        return {"error": "未找到两岸词典板块"}

    result = {
        "lianganTitle": "两岸词典",
        "data": {}
    }

    # 提取标题
    header_h2 = liangan_div.find('h2')
    if header_h2:
        result["data"]["title"] = header_h2.get_text().strip()

    # 定位到内容主体
    content_body = liangan_div.find('div', class_='content-card-body')
    if content_body:
        # 提取拼音导航
        pinyin_nav = extract_liangan_pinyin_navigation(content_body)
        if pinyin_nav:
            result["data"]["pinyin_navigation"] = pinyin_nav

        # 提取主要内容
        zi_contents = content_body.find('div', class_='zi-contents')
        if zi_contents:
            main_content = extract_liangan_main_content(zi_contents)
            if main_content:
                result["data"]["main_content"] = main_content

        # 提取注释说明
        zi_notes = content_body.find('div', class_='zi-notes')
        if zi_notes:
            result["data"]["notes"] = zi_notes.get_text().strip()

    return result


def extract_liangan_pinyin_navigation(content_body):
    """
    提取两岸词典的拼音导航信息
    """
    pinyin_nav = content_body.find('div', class_='zi-pinyin-nav')
    if not pinyin_nav:
        return None

    zi_pinyin_div = pinyin_nav.find('div', class_='zi-pinyin')
    if not zi_pinyin_div:
        return None

    pinyin_links = zi_pinyin_div.find_all('a')
    pinyin_list = []

    for link in pinyin_links:
        if 'active' in link.get('class', []):
            pinyin_list.append({
                "type": "全部",
                "pinyin": "全部",
                "active": True
            })
        elif 'pinyin' in link.get('class', []):
            # 提取拼音和上标数字
            pinyin_text = link.get_text().strip()
            # 解析如 "wáng<sup><small>1</small></sup>" 的格式
            sup_tag = link.find('sup')
            if sup_tag:
                small_tag = sup_tag.find('small')
                index_num = small_tag.get_text().strip() if small_tag else ""
                # 移除上标部分获取纯拼音
                base_pinyin = pinyin_text.replace(sup_tag.get_text(), "").strip()
            else:
                base_pinyin = pinyin_text
                index_num = ""

            pinyin_list.append({
                "type": "pinyin",
                "pinyin": base_pinyin,
                "index": index_num,
                "active": False
            })

    return {
        "pinyin_count": zi_pinyin_div.get('data-length', len(pinyin_list)),
        "pinyin_list": pinyin_list
    }


def extract_liangan_main_content(zi_contents_div):
    """
    提取两岸词典的主要内容（按拼音分组的内容）
    """
    # 查找所有 zi-content
    zi_contents = zi_contents_div.find_all('div', class_='zi-content')

    all_contents = []

    for zi_content in zi_contents:
        content_data = extract_liangan_single_pinyin_content(zi_content)
        if content_data:
            all_contents.append(content_data)

    return all_contents


def extract_liangan_single_pinyin_content(zi_content_div):
    """
    提取两岸词典单个拼音的内容
    """
    content_data = {}

    # 提取汉字标题、索引号和拼音信息
    main_heading = zi_content_div.find('div', class_='zi-heading main')
    if main_heading:
        # 提取汉字
        character_h3 = main_heading.find('h3')
        if character_h3:
            content_data["character"] = character_h3.get_text().strip()

        # 提取索引号（上标）
        sup_tag = main_heading.find('sup')
        if sup_tag:
            content_data["index"] = sup_tag.get_text().strip()

        # 提取拼音信息
        voice_span = main_heading.find('span', class_='voice')
        if voice_span:
            pinyin_info = extract_liangan_pinyin_info(voice_span)
            content_data["pinyin_info"] = pinyin_info

    # 提取详细解释
    detail_explain_div = zi_content_div.find('div', class_='zi-detail-explain')
    if detail_explain_div:
        explanations = extract_liangan_detailed_explanations(detail_explain_div)
        content_data["detailed_explanations"] = explanations

    return content_data if content_data else None


def extract_liangan_pinyin_info(voice_span):
    """
    提取两岸词典的拼音信息
    """
    py_em = voice_span.find('em', class_='py')
    zy_em = voice_span.find('em', class_='zy')
    voice_data = voice_span.get('data-voice', '')

    return {
        'pinyin': py_em.get_text().strip() if py_em else '',
        'zhuyin': zy_em.get_text().strip() if zy_em else '',
        'audio_file': voice_data
    }


def extract_liangan_detailed_explanations(detail_explain_div):
    """
    提取两岸词典的详细解释
    """
    explanations = []

    # 获取所有解释段落
    explain_paragraphs = detail_explain_div.find_all('p', class_='explain')

    for explain_p in explain_paragraphs:
        explanation_item = extract_liangan_explain_paragraph(explain_p)
        if explanation_item:
            explanations.append(explanation_item)

    return explanations


def extract_liangan_explain_paragraph(explain_p):
    """
    提取两岸词典的单个解释段落，包括例子等额外信息
    使用与其他板块相同的修复逻辑来处理extra元素
    """
    no_span = explain_p.find('span', class_='no')

    explanation_item = {
        "number": no_span.get_text().strip() if no_span else "",
        "content": explain_p.get_text().strip(),
        "examples": []
    }

    # 获取父级 zi-detail-explain 容器
    zi_detail_explain = explain_p.find_parent('div', class_='zi-detail-explain')
    if zi_detail_explain:
        # 找到所有的explain段落，记录当前explain的位置
        all_explains = zi_detail_explain.find_all('p', class_='explain')
        current_explain_index = None

        for i, explain in enumerate(all_explains):
            if explain == explain_p:  # 直接比较对象引用
                current_explain_index = i
                break

        # 如果找到了当前explain的位置
        if current_explain_index is not None:
            # 找到所有的extra元素
            extra_elements = zi_detail_explain.find_all('p', class_='extra')

            # 为当前explain分组对应的extra元素
            extra_groups = {}

            for extra in extra_elements:
                # 找到extra前面最近的explain
                prev_explain = None
                prev_sibling = extra.previous_sibling

                while prev_sibling:
                    if (hasattr(prev_sibling, 'name') and
                        prev_sibling.name == 'p' and
                        'explain' in prev_sibling.get('class', [])):
                        prev_explain = prev_sibling
                        break
                    prev_sibling = prev_sibling.previous_sibling

                # 如果这个extra前面有explain，就分组
                if prev_explain:
                    for i, explain in enumerate(all_explains):
                        if explain == prev_explain:
                            if i not in extra_groups:
                                extra_groups[i] = []
                            extra_groups[i].append(extra)
                            break

            # 获取当前explain对应的extra元素
            if current_explain_index in extra_groups:
                for extra in extra_groups[current_explain_index]:
                    # 提取内容
                    content_span = extra.find('span')
                    content = content_span.get_text().strip() if content_span else ""

                    # 根据类名确定内容类型
                    classes = extra.get('class', [])
                    if 'eg' in classes:
                        explanation_item["examples"] = content
                    elif 'quotes' in classes:
                        explanation_item["quotes"] = content

    return explanation_item


def extract_all_character_data(url):
    """
    爬取汉字的所有信息：基本信息 + 概述信息 + 意思信息 + 字源字形数据
    返回包含完整信息的字典
    """
    try:
        # 获取基本信息
        basic_info = extract_basic_info_from_url(url)

        # 获取概述信息
        gaishu_info = extract_gaishu_from_url(url)

        # 获取意思信息
        yisi_info = extract_yisi_from_url(url)

        # 获取字源字形数据
        evolution_data = extract_evolution_data(url)

        # 获取翻译信息
        fanyi_info = extract_fanyi_from_url(url)

        # 获取国语辞典信息
        guoyu_info = extract_guoyu_from_url(url)

        # 获取两岸词典信息
        liangan_info = extract_liangan_from_url(url)

        # 合并数据
        combined_data = {
            "url": url,
            "unicode_decimal": extract_character_from_url(url),
            "basic_info": basic_info,
            "gaishu_info": gaishu_info,
            "yisi_info": yisi_info,
            "fanyi_info": fanyi_info,
            "guoyu_info": guoyu_info,
            "liangan_info": liangan_info,
            "evolution_data": evolution_data
        }

        return combined_data

    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "unicode_decimal": extract_character_from_url(url)
        }


def crawl_all_hanzi(start_unicode=0x4E00, end_unicode=0x9FFF, save_to_database=True):
    """
    遍历所有Unicode汉字并爬取基本信息和字源字形数据保存到数据库
    主要覆盖基本汉字区：0x4E00-0x9FFF

    Args:
        start_unicode: 起始Unicode编码
        end_unicode: 结束Unicode编码
        save_to_database: 是否保存到数据库（默认为True）
    """
    base_url = "https://www.hanyuguoxue.com/zidian/zi-"
    total_characters = 0
    successful_crawls = 0
    failed_crawls = 0
    all_character_data = []

    print(f"开始爬取Unicode汉字范围：{start_unicode:#x} - {end_unicode:#x}")
    print(f"预计总汉字数：{end_unicode - start_unicode + 1}")
    print(f"保存方式: {'数据库' if save_to_database else '内存'}")
    print("同时爬取：基本信息 + 概述信息 + 意思信息 + 字源字形数据 + 翻译 + 国语辞典 + 两岸词典")
    print("=" * 60)

    for unicode_decimal in range(start_unicode, end_unicode + 1):
        try:
            # 构建URL
            url = f"{base_url}{unicode_decimal}"

            # 爬取完整数据（基本信息 + 概述 + 意思 + 字源字形 + 翻译等）
            character_data = extract_all_character_data(url)

            # 检查是否成功获取到数据
            if ('basic_info' in character_data and 'data' in character_data['basic_info'] and
                'character' in character_data['basic_info']['data']):

                total_characters += 1
                successful_crawls += 1

                basic_data = character_data['basic_info']['data']
                character = basic_data['character']

                # 保存到数据库
                if save_to_database:
                    if save_character_to_db(character_data):
                        # 显示爬取进度
                        if successful_crawls % 50 == 1 or successful_crawls <= 10:
                            print(f"【{successful_crawls:4d}】成功保存到数据库：{character} (Unicode: {unicode_decimal})")

                            # 显示基本信息
                            print(f"  拼音: {', '.join([p['pinyin'] for p in basic_data.get('pinyin_info', [])])}")
                            print(f"  部首: {basic_data.get('bushou_detail', {}).get('text', 'N/A')}")
                            print(f"  笔画: {basic_data.get('total_strokes', {}).get('text', 'N/A')}")
                            print(f"  结构: {basic_data.get('structure', 'N/A')}")
                            print(f"  造字法: {basic_data.get('formation_method', 'N/A')}")

                            # 显示字源字形统计
                            evolution_count = len(character_data.get('evolution_data', []))
                            print(f"  字源字形数量: {evolution_count}条")

                            if evolution_count > 0:
                                # 显示第一个字源字形作为示例
                                first_evolution = character_data['evolution_data'][0]
                                print(f"  首个字形: {first_evolution.get('alt', 'N/A')}")
                                print(f"  图片: {first_evolution.get('image_url', 'N/A')}")

                            print("-" * 40)
                    else:
                        failed_crawls += 1
                else:
                    # 保存到内存列表（原有逻辑）
                    all_character_data.append(character_data)

                    # 显示爬取进度
                    if successful_crawls % 10 == 1 or successful_crawls <= 10:
                        print(f"【{successful_crawls:4d}】汉字：{character} (Unicode: {unicode_decimal})")

                        # 显示基本信息
                        print(f"  拼音: {', '.join([p['pinyin'] for p in basic_data.get('pinyin_info', [])])}")
                        print(f"  部首: {basic_data.get('bushou_detail', {}).get('text', 'N/A')}")
                        print(f"  笔画: {basic_data.get('total_strokes', {}).get('text', 'N/A')}")
                        print(f"  结构: {basic_data.get('structure', 'N/A')}")
                        print(f"  造字法: {basic_data.get('formation_method', 'N/A')}")

                        # 显示字源字形统计
                        evolution_count = len(character_data.get('evolution_data', []))
                        print(f"  字源字形数量: {evolution_count}条")

                        if evolution_count > 0:
                            # 显示第一个字源字形作为示例
                            first_evolution = character_data['evolution_data'][0]
                            print(f"  首个字形: {first_evolution.get('alt', 'N/A')}")
                            print(f"  图片: {first_evolution.get('image_url', 'N/A')}")

                        print("-" * 40)

            else:
                failed_crawls += 1
                # 每100个失败显示一次进度
                if failed_crawls % 100 == 1:
                    print(f"  当前进度: Unicode {unicode_decimal}, 失败数: {failed_crawls}")

        except Exception as e:
            failed_crawls += 1
            # 静默处理错误，避免过多输出
            if failed_crawls % 100 == 1:
                print(f"遇到错误，当前失败数：{failed_crawls}")
            continue

        # 每处理1000个汉字显示一次进度
        if (unicode_decimal - start_unicode + 1) % 1000 == 0:
            progress = (unicode_decimal - start_unicode + 1) / (end_unicode - start_unicode + 1) * 100
            print(f"进度: {progress:.1f}% (成功: {successful_crawls}, 失败: {failed_crawls})")

    print("=" * 60)
    print(f"爬取完成！")
    print(f"总共Unicode汉字数：{end_unicode - start_unicode + 1}")
    print(f"成功爬取的汉字数：{successful_crawls}")
    print(f"失败的爬取数：{failed_crawls}")
    print(f"实际有数据的汉字数：{total_characters}")
    print(f"成功率：{successful_crawls/(successful_crawls+failed_crawls)*100:.2f}%")

    if save_to_database:
        print(f"数据已保存到数据库: lab_education.hanyuguoxue_hanzi")
    else:
        # 保存到文件（原有逻辑）
        if all_character_data:
            filename = f"hanzi_data_{start_unicode}_{end_unicode}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_character_data, f, ensure_ascii=False, indent=2)
            print(f"数据已保存到文件: {filename}")
            print(f"文件大小: {len(json.dumps(all_character_data, ensure_ascii=False))/1024/1024:.2f} MB")
            return all_character_data

    return None


def test_complete_extraction():
    """
    测试完整数据提取功能
    """
    print("测试汉字完整信息爬取：")
    wang_url = "https://www.hanyuguoxue.com/zidian/zi-29579"

    try:
        # 测试完整数据提取
        all_data = extract_all_character_data(wang_url)

        print("=" * 60)
        print(f"汉字URL: {all_data['url']}")
        print(f"Unicode编码: {all_data['unicode_decimal']}")
        print("=" * 60)

        # 打印基本信息
        if 'basic_info' in all_data and 'data' in all_data['basic_info']:
            basic_data = all_data['basic_info']['data']
            print(f"汉字: {basic_data.get('character', 'N/A')}")

            if 'pinyin_info' in basic_data:
                print("拼音信息:")
                for i, pinyin in enumerate(basic_data['pinyin_info']):
                    print(f"  {i+1}. 拼音: {pinyin.get('pinyin', 'N/A')}")
                    print(f"     注音: {pinyin.get('zhuyin', 'N/A')}")
                    print(f"     音频: {pinyin.get('audio_file', 'N/A')}")

            print(f"部首: {basic_data.get('bushou_detail', {}).get('text', 'N/A')}")
            print(f"总笔画: {basic_data.get('total_strokes', {}).get('text', 'N/A')}")
            print(f"结构: {basic_data.get('structure', 'N/A')}")
            print(f"造字法: {basic_data.get('formation_method', 'N/A')}")
            print(f"五行: {basic_data.get('five_elements', 'N/A')}")
            print(f"五笔: {basic_data.get('wubi', 'N/A')}")
            print(f"仓颉: {basic_data.get('cangjie', 'N/A')}")

            if 'variant_characters' in basic_data:
                variant_chars = [vc['character'] for vc in basic_data['variant_characters']]
                print(f"异体字: {', '.join(variant_chars)}")

        print("\n" + "-" * 40)

        # 打印字源字形信息
        if 'evolution_data' in all_data and all_data['evolution_data']:
            print("字源字形 (前2条):")
            for i, data in enumerate(all_data['evolution_data'][:2]):
                print(f"  {i+1}. 字形: {data.get('alt', 'N/A')}")
                print(f"     时期: {data.get('period', 'N/A')}")
                print(f"     风格: {data.get('style', 'N/A')}")
                print(f"     来源: {data.get('source', 'N/A')}")
                print(f"     图片: {data.get('image_url', 'N/A')}")

        print("\n完整JSON数据:")
        print(json.dumps(all_data, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"测试失败: {e}")


def test_small_range_crawl():
    """
    测试小范围汉字爬取（用于调试）
    """
    print("测试小范围汉字爬取：")
    print("爬取范围：王(29579)、玉(29577)等几个常用汉字")
    print("=" * 60)

    # 测试几个常用汉字
    test_characters = [29579, 29577, 20013, 22823]  # 王、玉、中、大

    for unicode_decimal in test_characters:
        try:
            url = f"https://www.hanyuguoxue.com/zidian/zi-{unicode_decimal}"
            character_data = extract_all_character_data(url)

            if ('basic_info' in character_data and 'data' in character_data['basic_info'] and
                'character' in character_data['basic_info']['data']):

                basic_data = character_data['basic_info']['data']
                character = basic_data['character']

                print(f"汉字：{character} (Unicode: {unicode_decimal})")

                # 打印完整的JSON数据
                print("完整JSON数据:")
                print(json.dumps(character_data, ensure_ascii=False, indent=2))

                print("-" * 60)
            else:
                print(f"Unicode {unicode_decimal}: 未能获取到数据")

        except Exception as e:
            print(f"Unicode {unicode_decimal}: 错误 - {e}")

# ================= 数据库相关函数 =================

def get_database_connection():
    """
    获取数据库连接
    """
    try:
        connection = pymysql.connect(
            host=mysql_config["host"],
            user=mysql_config["user"],
            password=mysql_config["password"],
            database=mysql_config["database"],
            port=mysql_config["port"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None


def save_character_to_db(character_data):
    """
    将汉字数据保存到数据库
    """
    connection = get_database_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()

        # 提取汉字字符
        character = ""
        if 'basic_info' in character_data and 'data' in character_data['basic_info']:
            character = character_data['basic_info']['data'].get('character', '')

        # 如果有错误信息，保存错误记录
        if 'error' in character_data:
            sql = """
            INSERT INTO hanyuguoxue_hanzi
            (`character`, url, unicode_decimal, `error`)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            url = VALUES(url),
            unicode_decimal = VALUES(unicode_decimal),
            `error` = VALUES(`error`),
            updated_at = CURRENT_TIMESTAMP
            """
            cursor.execute(sql, (
                character,
                character_data.get('url', ''),
                character_data.get('unicode_decimal', ''),
                character_data['error']
            ))
        else:
            # 保存完整数据
            sql = """
            INSERT INTO hanyuguoxue_hanzi
            (`character`, url, unicode_decimal, basic_info, gaishu_info, yisi_info,
             fanyi_info, guoyu_info, liangan_info, evolution_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            url = VALUES(url),
            unicode_decimal = VALUES(unicode_decimal),
            basic_info = VALUES(basic_info),
            gaishu_info = VALUES(gaishu_info),
            yisi_info = VALUES(yisi_info),
            fanyi_info = VALUES(fanyi_info),
            guoyu_info = VALUES(guoyu_info),
            liangan_info = VALUES(liangan_info),
            evolution_data = VALUES(evolution_data),
            updated_at = CURRENT_TIMESTAMP
            """
            cursor.execute(sql, (
                character,
                character_data.get('url', ''),
                character_data.get('unicode_decimal', ''),
                json.dumps(character_data.get('basic_info', {}), ensure_ascii=False),
                json.dumps(character_data.get('gaishu_info', {}), ensure_ascii=False),
                json.dumps(character_data.get('yisi_info', {}), ensure_ascii=False),
                json.dumps(character_data.get('fanyi_info', {}), ensure_ascii=False),
                json.dumps(character_data.get('guoyu_info', {}), ensure_ascii=False),
                json.dumps(character_data.get('liangan_info', {}), ensure_ascii=False),
                json.dumps(character_data.get('evolution_data', []), ensure_ascii=False)
            ))

        connection.commit()
        return True

    except Exception as e:
        print(f"保存数据到数据库失败: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()



def crawl_all_hanzi_to_db(start_unicode=0x4E00, end_unicode=0x9FFF):
    """
    遍历所有Unicode汉字并爬取数据保存到数据库
    主要覆盖基本汉字区：0x4E00-0x9FFF
    """
    base_url = "https://www.hanyuguoxue.com/zidian/zi-"

    total_characters = 0
    successful_crawls = 0
    failed_crawls = 0

    print(f"开始爬取Unicode汉字范围：{start_unicode:#x} - {end_unicode:#x}")
    print(f"预计总汉字数：{end_unicode - start_unicode + 1}")
    print("同时爬取：基本信息 + 概述信息 + 意思信息 + 字源字形数据，保存到数据库")
    print("=" * 60)

    for unicode_decimal in range(start_unicode, end_unicode + 1):
        try:
            # 构建URL
            url = f"{base_url}{unicode_decimal}"

            # 爬取完整数据（基本信息 + 概述 + 意思 + 字源字形）
            character_data = extract_all_character_data(url)

            # 保存到数据库
            if save_character_to_db(character_data):
                successful_crawls += 1

                # 检查是否成功获取到数据
                if ('basic_info' in character_data and 'data' in character_data['basic_info'] and
                    'character' in character_data['basic_info']['data']):
                    total_characters += 1

                    # 显示爬取进度
                    if successful_crawls % 50 == 1 or successful_crawls <= 10:
                        basic_data = character_data['basic_info']['data']
                        character = basic_data['character']
                        print(f"【{successful_crawls:4d}】成功保存到数据库：{character} (Unicode: {unicode_decimal})")

                        # 显示基本信息
                        print(f"  拼音: {', '.join([p['pinyin'] for p in basic_data.get('pinyin_info', [])])}")
                        print(f"  部首: {basic_data.get('bushou_detail', {}).get('text', 'N/A')}")
                        print(f"  笔画: {basic_data.get('total_strokes', {}).get('text', 'N/A')}")
                        print(f"  结构: {basic_data.get('structure', 'N/A')}")
                        print(f"  造字法: {basic_data.get('formation_method', 'N/A')}")

                        # 显示字源字形统计
                        evolution_count = len(character_data.get('evolution_data', []))
                        print(f"  字源字形数量: {evolution_count}条")
                        print("-" * 40)
            else:
                failed_crawls += 1

        except Exception as e:
            failed_crawls += 1
            continue

        # 每处理1000个汉字显示一次进度
        if (unicode_decimal - start_unicode + 1) % 1000 == 0:
            progress = (unicode_decimal - start_unicode + 1) / (end_unicode - start_unicode + 1) * 100
            print(f"进度: {progress:.1f}% (成功: {successful_crawls}, 失败: {failed_crawls})")

    print("=" * 60)
    print(f"爬取完成！")
    print(f"总共Unicode汉字数：{end_unicode - start_unicode + 1}")
    print(f"成功保存到数据库: {successful_crawls}")
    print(f"失败的爬取数: {failed_crawls}")
    print(f"实际有数据的汉字数：{total_characters}")
    print(f"成功率：{successful_crawls/(successful_crawls+failed_crawls)*100:.2f}%")


if __name__ == "__main__":

    # 测试爬取小范围数据到数据库
    print("测试爬取前16个汉字到数据库...")
    crawl_all_hanzi(start_unicode=0x4E00, end_unicode=0x4E0F, save_to_database=True)  # 爬取前16个汉字测试

    print("\n" + "="*60 + "\n")

    # 可以选择性地运行全量爬取到数据库
    # 取消注释下面的行来运行全量爬取
    # print("开始爬取所有汉字到数据库...")
    # crawl_all_hanzi(save_to_database=True)  # 保存到数据库

    # 或者爬取特定范围到数据库
    # print("爬取常用汉字范围（前100个）到数据库...")
    # crawl_all_hanzi(start_unicode=0x4E00, end_unicode=0x4E63, save_to_database=True)

    print("测试完成！如需爬取完整数据，请取消注释相应的爬取代码。")