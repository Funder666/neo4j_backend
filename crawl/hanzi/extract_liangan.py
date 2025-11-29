import re
import json
from bs4 import BeautifulSoup


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
    time.sleep(1)  # 延时1s

    return extract_liangan_from_html(html_content)


def extract_liangan_from_html(html_content):
    """
    从HTML内容中提取两岸词典信息（不访问URL）
    """
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
        pinyin_nav = extract_pinyin_navigation(content_body)
        if pinyin_nav:
            result["data"]["pinyin_navigation"] = pinyin_nav

        # 提取主要内容
        zi_contents = content_body.find('div', class_='zi-contents')
        if zi_contents:
            main_content = extract_main_content(zi_contents)
            if main_content:
                result["data"]["main_content"] = main_content

        # 提取注释说明
        zi_notes = content_body.find('div', class_='zi-notes')
        if zi_notes:
            result["data"]["notes"] = zi_notes.get_text().strip()

    return result


def extract_pinyin_navigation(content_body):
    """
    提取拼音导航信息
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


def extract_main_content(zi_contents_div):
    """
    提取主要内容（按拼音分组的内容）
    """
    # 查找所有 zi-content
    zi_contents = zi_contents_div.find_all('div', class_='zi-content')

    all_contents = []

    for zi_content in zi_contents:
        content_data = extract_single_pinyin_content(zi_content)
        if content_data:
            all_contents.append(content_data)

    return all_contents


def extract_single_pinyin_content(zi_content_div):
    """
    提取单个拼音的内容
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
            pinyin_info = extract_pinyin_info(voice_span)
            content_data["pinyin_info"] = pinyin_info

    # 提取详细解释
    detail_explain_div = zi_content_div.find('div', class_='zi-detail-explain')
    if detail_explain_div:
        explanations = extract_detailed_explanations(detail_explain_div)
        content_data["detailed_explanations"] = explanations

    return content_data if content_data else None


def extract_pinyin_info(voice_span):
    """
    提取拼音信息
    """
    py_em = voice_span.find('em', class_='py')
    zy_em = voice_span.find('em', class_='zy')
    voice_data = voice_span.get('data-voice', '')

    return {
        'pinyin': py_em.get_text().strip() if py_em else '',
        'zhuyin': zy_em.get_text().strip() if zy_em else '',
        'audio_file': voice_data
    }


def extract_detailed_explanations(detail_explain_div):
    """
    提取详细解释
    """
    explanations = []

    # 获取所有解释段落
    explain_paragraphs = detail_explain_div.find_all('p', class_='explain')

    for explain_p in explain_paragraphs:
        explanation_item = extract_explain_paragraph(explain_p)
        if explanation_item:
            explanations.append(explanation_item)

    return explanations


def extract_explain_paragraph(explain_p):
    """
    提取单个解释段落，包括例子等额外信息
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


def test_extract_liangan():
    """
    测试两岸词典信息提取功能
    """
    # 测试HTML片段
    test_html = '''<div class="card" data-id="两岸词典"><div class="content-card" style="position: relative;"><div class="sticky-events--sentinel sticky-events--sentinel-top" style="left: 0px; position: relative; right: 0px; visibility: hidden; top: calc(-51px);"></div><div class="content-card-header outer" style="position: sticky;"><h2 id="liangancidian">王的两岸词典解释</h2><div aria-expanded="true" data-toggle="collapse" href="#lacd"><span class="fold">折叠</span><span class="unfold">展开</span><span class="arrow"><i class="iconfont icon-arrowdown"></i></span></div></div><div class="content-card-body show" id="lacd"><div class="content-nav-list zi-pinyin-nav"><div class="list scroll-x"><div class="wrap d-flex zi-pinyin" data-length="2" style="min-width:100%"><a class="active" href="#">全部</a><a class="pinyin" href="#">wáng<sup><small>1</small></sup></a><a class="pinyin" href="#">wàng<sup><small>2</small></sup></a></div></div></div><div class="zi-contents"><div class="zi-content"><div class="zi-heading main" data-id="两岸词典-0-0"><h3 class="zi-title">王</h3><sup>1</sup><span class="voice" data-voice="wang2.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"><em class="py">wáng</em><em class="zy">ㄨㄤˊ</em></span></div><div class="zi-heading secondary"><h4 data-id="两岸词典-0-0-0">详细解释</h4><span><input checked="" class="switch" id="gycd0" type="checkbox"><label for="gycd0">例证</label></span></div><div class="zi-detail-explain"><p class="explain"><span class="no">1.</span>君主制国家的君主；国君。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>君王、国王、帝王。</span></p><p class="explain"><span class="no">2.</span>秦汉以后封建社会中最高的爵位。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>亲王、王公、王侯。</span></p><p class="explain"><span class="no">3.</span>首领；头目。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>山大王、万兽之王、擒贼先擒王。</span></p><p class="explain"><span class="no">4.</span>泛称团体中表现最优秀的；技艺超群。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>歌王、拳王、王牌。</span></p><p class="explain"><span class="no">5.</span>古代对祖父母辈的尊称。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>王父（祖父）、王母（祖母）。</span></p><p class="explain"><span class="no">6.</span>姓。</p></div></div><div class="zi-content"><div class="zi-heading main" data-id="两岸词典-0-1"><h3 class="zi-title">王</h3><sup>2</sup><span class="voice" data-voice="wang4.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"><em class="py">wàng</em><em class="zy">ㄨㄤˋ</em></span></div><div class="zi-heading secondary"><h4 data-id="两岸词典-0-1-0">详细解释</h4><span><input checked="" class="switch" id="gycd1" type="checkbox"><label for="gycd1">例证</label></span></div><div class="zi-detail-explain"><p class="explain"><span class="no">1.</span>《书》古代指君临天下。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>王天下、王此大邦。</span></p><p class="explain"><span class="no">2.</span>《书》行王道；以仁义治国。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>以德行仁者王，王不待大。</span></p></div></div></div><div class="zi-notes">注：两岸词典来源于中华文化总会</div></div><div class="sticky-events--sentinel sticky-events--sentinel-bottom" style="left: 0px; position: relative; right: 0px; visibility: hidden; bottom: 51px; height: 38px;"></div></div></div>'''

    # 提取两岸词典信息
    liangan_data = extract_liangan_from_html(test_html)

    print("两岸词典信息提取测试：")
    print("=" * 60)
    print(json.dumps(liangan_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_extract_liangan()