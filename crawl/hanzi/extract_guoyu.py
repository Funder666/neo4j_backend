import re
import json
from bs4 import BeautifulSoup


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
    time.sleep(1)  # 延时1s

    return extract_guoyu_from_html(html_content)


def extract_guoyu_from_html(html_content):
    """
    从HTML内容中提取国语辞典信息（不访问URL）
    """
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
            main_content = extract_main_content(zi_contents)
            if main_content:
                result["data"]["main_content"] = main_content

        # 提取注释说明
        zi_notes = content_body.find('div', class_='zi-notes')
        if zi_notes:
            result["data"]["notes"] = zi_notes.get_text().strip()

    return result


def extract_main_content(zi_contents_div):
    """
    提取主要内容（汉字信息和详细解释）
    """
    # 查找所有 zi-content
    zi_contents = zi_contents_div.find_all('div', class_='zi-content')

    all_contents = []

    for zi_content in zi_contents:
        content_data = extract_single_zi_content(zi_content)
        if content_data:
            all_contents.append(content_data)

    return all_contents


def extract_single_zi_content(zi_content_div):
    """
    提取单个 zi-content 的内容
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
    提取详细解释，按词性分组
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


def test_extract_guoyu():
    """
    测试国语辞典信息提取功能
    """
    # 测试HTML片段
    test_html = '''<div class="card" data-id="国语辞典"><div class="content-card" style="position: relative;"><div class="sticky-events--sentinel sticky-events--sentinel-top" style="left: 0px; position: relative; right: 0px; visibility: hidden; top: calc(-51px);"></div><div class="content-card-header outer" style="position: sticky;"><h2 id="guoyucidian">王的国语辞典解释</h2><div aria-expanded="true" data-toggle="collapse" href="#gycd"><span class="fold">折叠</span><span class="unfold">展开</span><span class="arrow"><i class="iconfont icon-arrowdown"></i></span></div></div><div class="content-card-body show" id="gycd"><div class="content-nav-list zi-pinyin-nav"><div class="list scroll-x"><div class="wrap d-flex zi-pinyin" data-length="3" style="min-width:100%"><a class="active" href="#">全部</a><a class="pinyin" href="#">wáng<sup><small>1</small></sup></a><a class="pinyin" href="#">yù<sup><small>2</small></sup></a><a class="pinyin" href="#">wàng<sup><small>3</small></sup></a></div></div></div><div class="zi-contents"><div class="zi-content"><div class="zi-heading main" data-id="国语辞典-0-0"><h3 class="zi-title">王</h3><sup>1</sup><span class="voice" data-voice="wang2.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"><em class="py">wáng</em><em class="zy">ㄨㄤˊ</em></span></div><div class="zi-heading secondary"><h4 data-id="国语辞典-0-0-0">详细解释</h4><span><input checked="" class="switch" id="gycd0" type="checkbox"><label for="gycd0">例证</label></span></div><div class="zi-detail-explain"><p class="cixing">名</p><p class="explain"><span class="no">1.</span>古代称统治天下的君主。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>《书经 · 洪范》：“天子作民父母，以为天下王。”</span></p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>君王、帝王、国王。</span></p><p class="explain"><span class="no">2.</span>古代封建社会中地位在公侯之上的爵位。秦汉以后，天子的伯叔兄弟及异姓藩王均称为“<a class="primary" href="/zidian/zi-29579" title="王">王</a>”。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>《汉书 · 卷一九 · 百官公卿表上》：“诸侯王，高帝初置，金玺盭绶，掌治其国。”</span></p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>淮南王。</span></p><p class="explain"><span class="no">3.</span>泛称同类中的首领。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>唐 · 杜甫《前出塞》诗九首之六：“射人先射马，擒贼先擒王。”</span><span>《西游记 · 第一回》：“那一个有本事的，钻进去寻个源头出来，不伤身体者，我等即拜他为王。”</span></p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>万兽之王。</span></p><p class="explain"><span class="no">4.</span>技艺超群的人。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>歌王、拳王。</span></p><p class="explain"><span class="no">5.</span>古代对祖父母辈的尊称。参见“王父”、“王母”等条。</p><p class="explain"><span class="no">6.</span>姓。如宋代有王安石。</p><p class="cixing">动</p><p class="explain"><span class="no">◎</span>古代诸侯朝见天子。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>《诗经 · 商颂 · 殷武》：“莫敢不来享，莫敢不来王。”</span><span>《史记 · 卷四 · 周本纪》：“要服者贡，荒服者王。”</span></p><p class="cixing">形</p><p class="explain"><span class="no">◎</span>大。参见“王虺”、“王鲔”等条。</p></div></div><div class="zi-content"><div class="zi-heading main" data-id="国语辞典-0-1"><h3 class="zi-title">王</h3><sup>2</sup><span class="voice" data-voice="yu4.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"><em class="py">yù</em><em class="zy">ㄩˋ</em></span></div><div class="zi-heading secondary"><h4 data-id="国语辞典-0-1-0">详细解释</h4><span><input checked="" class="switch" id="gycd1" type="checkbox"><label for="gycd1">例证</label></span></div><div class="zi-detail-explain"><p class="explain"><span class="no">◎</span></p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>《广韵 · 入声 · 烛韵》：“玉，说文本作王，隶加点以别王字。”</span></p></div></div><div class="zi-content"><div class="zi-heading main" data-id="国语辞典-0-2"><h3 class="zi-title">王</h3><sup>3</sup><span class="voice" data-voice="wang4.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"><em class="py">wàng</em><em class="zy">ㄨㄤˋ</em></span></div><div class="zi-heading secondary"><h4 data-id="国语辞典-0-2-0">详细解释</h4><span><input checked="" class="switch" id="gycd2" type="checkbox"><label for="gycd2">例证</label></span></div><div class="zi-detail-explain"><p class="cixing">动</p><p class="explain"><span class="no">◎</span>统治天下、称王。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>《诗经 · 大雅 · 皇矣》：“王此大邦，克顺克比。”</span><span>《史记 · 卷七 · 项羽本纪》：“怀王与诸将约曰：‘先破秦入咸阳者王之’。”</span></p><p class="cixing">形</p><p class="explain"><span class="no">◎</span>兴盛、旺盛。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>《庄子 · 养生主》：“泽雉十步一啄，百步一饮，不蕲畜乎樊中，神虽王，不善也。”</span><span>唐 · 李白《赠张相镐》诗二首之二：“英烈遗厥孙，百代神犹王。”</span></p></div></div></div><div class="zi-notes">注：国语辞典来源于台湾重编国语辞典修订本</div></div><div class="sticky-events--sentinel sticky-events--sentinel-bottom" style="left: 0px; position: absolute; right: 0px; visibility: hidden; bottom: 51px; height: 38px;"></div></div></div>'''

    # 提取国语辞典信息
    guoyu_data = extract_guoyu_from_html(test_html)

    print("国语辞典信息提取测试：")
    print("=" * 60)
    print(json.dumps(guoyu_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_extract_guoyu()