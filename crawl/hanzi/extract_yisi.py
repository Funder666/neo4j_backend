import re
import json
from bs4 import BeautifulSoup


def extract_yisi_from_url(url):
    """
    从URL获取HTML并提取意思信息，返回JSON格式数据
    针对data-id="意思"板块进行解析
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

    # 定位到内容主体
    content_body = yisi_div.find('div', class_='content-card-body')
    if content_body:
        zi_contents = content_body.find_all('div', class_='zi-content')

        all_explanations = []

        for zi_content in zi_contents:
            # 提取主要内容
            main_content = extract_main_content(zi_content)
            if main_content:
                all_explanations.append(main_content)

            # 提取古壮字释义（如果存在）
            ancient_explanation = extract_ancient_explanation(zi_content)
            if ancient_explanation:
                all_explanations.append(ancient_explanation)

        result["data"]["explanations"] = all_explanations

    return result


def extract_main_content(zi_content_div):
    """
    提取主要内容（基本解释和详细解释）
    """
    # 跳过没有主要内容的zi-contents（古壮字释义通常没有main heading）
    main_heading = zi_content_div.find('div', class_='zi-heading main')
    if not main_heading:
        return None

    # 提取汉字标题和拼音
    character_h3 = main_heading.find('h3')
    character = character_h3.get_text().strip() if character_h3 else ""

    # 提取拼音信息
    pinyin_info = []
    voice_span = main_heading.find('span', class_='voice')
    if voice_span:
        py_em = voice_span.find('em', class_='py')
        zy_em = voice_span.find('em', class_='zy')
        voice_data = voice_span.get('data-voice', '')

        pinyin_info.append({
            'pinyin': py_em.get_text().strip() if py_em else '',
            'zhuyin': zy_em.get_text().strip() if zy_em else '',
            'audio_file': voice_data
        })

    main_explanation = {
        "character": character,
        "pinyin_info": pinyin_info,
        "basic_explanation": [],
        "detailed_explanation": []
    }

    # 提取基本解释
    basic_heading = zi_content_div.find('h4', string=lambda text: text and "基本解释" in text)
    if basic_heading:
        basic_explain_div = zi_content_div.find('div', class_='zi-basic-explain')
        if basic_explain_div:
            basic_explains = basic_explain_div.find_all('p', class_='explain')
            for p in basic_explains:
                # 提取序号和文本
                no_span = p.find('span', class_='no')
                text_span = p.find('span', class_='text')
                eg_span = p.find('span', class_='eg')

                basic_item = {
                    "number": no_span.get_text().strip() if no_span else "",
                    "explanation": text_span.get_text().strip() if text_span else "",
                    "example": eg_span.get_text().strip() if eg_span else "",
                    "full_text": p.get_text().strip()
                }
                main_explanation["basic_explanation"].append(basic_item)

    # 提取详细解释
    detail_heading = zi_content_div.find('h4', string=lambda text: text and "详细解释" in text)
    if detail_heading:
        detail_explain_div = zi_content_div.find('div', class_='zi-detail-explain')
        if detail_explain_div:
            # 按词性分组
            current_cixing = ""
            detail_explains = detail_explain_div.find_all(['p', 'div'], recursive=False)

            for element in detail_explains:
                if element.name == 'p' and 'cixing' in element.get('class', []):
                    # 词性标记
                    current_cixing = element.get_text().strip()
                elif element.name == 'p' and 'explain' in element.get('class', []):
                    # 解释条目 - 使用修复后的提取逻辑
                    detail_item = extract_detailed_explain_paragraph(element, current_cixing)
                    if detail_item:
                        main_explanation["detailed_explanation"].append(detail_item)

    return main_explanation


def extract_detailed_explain_paragraph(p_element, current_cixing):
    """
    提取详细解释段落，包括引证、例子、英文等额外信息
    使用修复后的逻辑，正确处理HTML结构中的extra元素
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


def extract_ancient_explanation(zi_content_div):
    """
    提取古壮字释义
    """
    ancient_heading = zi_content_div.find('h4', string=lambda text: text and "古壮字释义" in text)
    if not ancient_heading:
        return None

    ancient_explanation = {
        "type": "古壮字释义",
        "explanations": []
    }

    # 获取古壮字内容区域
    ancient_content = zi_content_div.find_next_sibling('div', class_='zi-content')
    if ancient_content:
        detail_explains = ancient_content.find_all('p', class_='explain')
        for p in detail_explains:
            no_span = p.find('span', class_='no')
            explanation_text = p.get_text().strip()

            ancient_item = {
                "number": no_span.get_text().strip() if no_span else "",
                "explanation": explanation_text,
                "full_text": explanation_text
            }
            ancient_explanation["explanations"].append(ancient_item)

    return ancient_explanation


def extract_yisi_from_html(html_content):
    """
    从HTML内容中提取意思信息（不访问URL）
    """
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

    # 定位到内容主体
    content_body = yisi_div.find('div', class_='content-card-body')
    if content_body:
        zi_contents = content_body.find_all('div', class_='zi-content')

        all_explanations = []

        for zi_content in zi_contents:
            # 提取主要内容
            main_content = extract_main_content(zi_content)
            if main_content:
                all_explanations.append(main_content)

            # 提取古壮字释义（如果存在）
            ancient_explanation = extract_ancient_explanation(zi_content)
            if ancient_explanation:
                all_explanations.append(ancient_explanation)

        result["data"]["explanations"] = all_explanations

    return result


def test_extract_yisi():
    """
    测试意思信息提取功能
    """
    # 测试HTML片段
    test_html = '''<div class="card" data-id="意思"><div class="content-card" style="position: relative;"><div class="sticky-events--sentinel sticky-events--sentinel-top" style="left: 0px; position: relative; right: 0px; visibility: hidden; top: calc(-51px);"></div><div class="content-card-header outer" style="position: sticky;"><h2 id="jieshi">王的意思</h2><a class="font-sm" data-feedback="" data-label="#内容解释"><i class="iconfont icon-help2"></i> 纠错</a></div><div class="content-card-body show" id="details"><div class="content-nav-list zi-pinyin-nav"><div class="list scroll-x"><div class="wrap d-flex zi-pinyin" data-length="2" style="min-width:100%"><a class="active" href="#">全部</a><a class="pinyin" href="#">wáng<sup><small>1</small></sup></a><a class="pinyin" href="#">wàng<sup><small>2</small></sup></a></div></div></div><div class="zi-contents"><div class="zi-content"><div class="zi-heading main" data-id="意思-0-0"><h3 class="zi-title">王</h3><sup>1</sup><span class="voice" data-voice="wang2.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"><em class="py">wáng</em><em class="zy">ㄨㄤˊ</em></span></div><div class="zi-heading secondary"><h4 class="mb-0" data-id="意思-0-0-0">基本解释</h4></div><div class="zi-basic-explain"><p class="explain"><span class="no">①</span><span class="text">古代一国君主的称号，现代有些国家仍用这种称号。</span><span class="eg"><label>例如</label>～国。～法。公子～孙。～朝（ cháo ）。</span></p><p class="explain"><span class="no">②</span><span class="text">中国古代皇帝以下的最高爵位。</span><span class="eg"><label>例如</label>～公。～侯。</span></p><p class="explain"><span class="no">③</span><span class="text">一族或一类中的首领。</span><span class="eg"><label>例如</label>山大～。蜂～。～牌（桥牌中最大的牌；喻最有力的人物或手段）。</span></p><p class="explain"><span class="no">④</span><span class="text">大。</span><span class="eg"><label>例如</label>～父（祖父）。～母（祖母）。</span></p><p class="explain"><span class="no">⑤</span><span class="text">姓。</span></p></div><div class="zi-heading secondary"><h4 class="mb-0" data-id="意思-0-0-1">详细解释</h4><span><input checked="" class="switch" id="xxjs0" type="checkbox"><label for="xxjs0">例证</label></span></div><div class="zi-detail-explain"><p class="cixing">名词</p><p class="explain"><span class="no">1.</span>象形字。王字的甲骨文为斧钺之形，斧钺为礼器，象征王者之权威。本义：天子、君主。</p><p class="explain"><span class="no">2.</span>殷周时代对帝王的称呼。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>溥天之下，莫非<mark>王</mark>土。 <span class="author"> 《诗 · 小雅 · 北土》</span></span><span>厉<mark>王</mark>虐，国人谤<mark>王</mark>。 <span class="author"> 《国语 · 周语上》</span></span><span><mark>王</mark>，天下所归往也。董仲舒曰：“古之造文者，三画而连其中谓之<mark>王</mark>。三者，天、地、人也；而参通之者，<mark>王</mark>也。” <span class="author"> 《说文》</span></span><span><mark>王</mark>，天子也。 <span class="author"> 《释名》</span></span><span><mark>王</mark>，有天下曰<mark>王</mark>。帝与<mark>王</mark>一也。周衰，列国皆僭号自<mark>王</mark>。 秦有天下，遂自尊为皇帝。 汉有天下，因 秦制称帝，封同姓为<mark>王</mark>，名始乱矣。 <span class="author"> 《六书故》</span></span><span>故百<mark>王</mark>之法不同。 <span class="author"> 《荀子 · 王霸》</span></span><span>制其守宰，不制其侯<mark>王</mark>。 <span class="author"> 柳宗元《封建论》</span></span><span>以<mark>王</mark>命聚之。 <span class="author"> 唐 · 柳宗元《捕蛇者说》</span></span></p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>王公（天子与诸侯；泛指达官贵人）；王土（天子的土地）；王士（天子的士民）；王宇（天子的宫殿）；王志（天子的意向）；王车（王之车乘）</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>emperor; monarch;</span></p><p class="explain"><span class="no">3.</span>春秋时，楚、吴、越等诸侯国国君也开始称“<a class="primary" href="/zidian/zi-29579" title="王">王</a>”，战国时各诸侯国国君普遍称“<a class="primary" href="/zidian/zi-29579" title="王">王</a>”。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>越<mark>王</mark>勾践栖于 会稽之上。 <span class="author"> 《国语 · 越语上》</span></span><span>请勾践女女于王。</span><span><mark>王</mark>好战，请以战喻。 <span class="author"> 《孟子 · 梁惠王上》</span></span></p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>王人（国君）；王女（古时封王者之女）；王吏（天子或国君的官吏）；王使（天子或王侯的使者）；王政（国君的政令）；王妃（侯王、太子之配偶；帝王之妾，位次于皇后）</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>king;</span></p><p class="explain"><span class="no">4.</span>从秦代开始，天子改称“皇帝”，“<a class="primary" href="/zidian/zi-29579" title="王">王</a>”便成了对贵族或功臣的最高封爵，即诸侯王。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>赐号称<mark>王</mark>。 <span class="author"> 《汉书 · 李广苏建传》</span></span><span><mark>王</mark>侯以下。 <span class="author"> 《后汉书 · 张衡传》</span></span></p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>西汉初，刘濞被封为吴王；韩信先被封为齐王，后改为楚王</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>prince;</span></p><p class="explain"><span class="no">5.</span>朝廷 。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>王庭，王廷（朝廷）；王役，王徭（朝廷的徭役）；王务（朝廷的公事）；王机（朝廷的政事）；王体（朝廷的大政方针）</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>court;</span></p><p class="explain"><span class="no">6.</span>王朝 。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>王轨（王朝的秩序、制度）；王制（王朝的制度）；王灵（王朝的威德）</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>dynasty;</span></p><p class="explain"><span class="no">7.</span>首领；同类中最突出者。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span><mark>王</mark>久不至。 <span class="author"> 唐 · 李朝威《柳毅传》</span></span></p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>擒贼先擒王；乐器之王；拜他为王</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>chief;</span></p><p class="explain"><span class="no">8.</span>中国古代对祖父母的尊称。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>父之考为<mark>王</mark>父，父之妣为<mark>王</mark>母，<mark>王</mark>父之考为曾祖<mark>王</mark>父，<mark>王</mark>父之妣为曾祖<mark>王</mark>母，曾祖<mark>王</mark>父之考，为高祖<mark>王</mark>父…。 <span class="author"> 《尔雅》</span></span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>grandfather, grandmother;</span></p><p class="explain"><span class="no">9.</span>统治者，主宰者 。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>王化（以仁义治天下的教化）；王官（宗藩王府的小职官）</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>ruler;</span></p><p class="explain"><span class="no">10.</span>冠军 。</p><p class="extra eg"><label>例如 <em class="sr-only">：</em></label><span>拳王</span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>champion;</span></p><p class="explain"><span class="no">11.</span>姓。</p><p class="explain"><span class="no">12.</span>另见 wàng。</p></div></div><div class="zi-content"><div class="zi-heading main" data-id="意思-0-1"><h3 class="zi-title">王</h3><sup>2</sup><span class="voice" data-voice="wang4.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"><em class="py">wàng</em><em class="zy">ㄨㄤˋ</em></span></div><div class="zi-heading secondary"><h4 class="mb-0" data-id="意思-0-1-0">基本解释</h4></div><div class="zi-basic-explain"><p class="explain"><span class="no">◎</span><span class="text">古代指统治者谓以仁义取得天下。</span><span class="eg"><label>例如</label>～天下。～此大邦。</span></p></div><div class="zi-heading secondary"><h4 class="mb-0" data-id="意思-0-1-1">详细解释</h4><span><input checked="" class="switch" id="xxjs1" type="checkbox"><label for="xxjs1">例证</label></span></div><div class="zi-detail-explain"><p class="cixing">动词</p><p class="explain"><span class="no">1.</span>统治、领有一国或一地。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span><mark>王</mark>此大邦，克顺克比。 <span class="author"> 《诗 · 大雅》</span></span><span>欲<mark>王</mark>关中。 <span class="author"> 《史记 · 项羽本纪》</span></span><span>秦地可尽王。</span><span>沛公为 汉<mark>王</mark>，<mark>王</mark> 巴、 蜀。 <span class="author"> 《史记 · 留侯世家》</span></span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>rule;</span></p><p class="explain"><span class="no">2.</span>作皇帝，称王。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>然而不<mark>王</mark>者，未之有也。 <span class="author"> 《孟子 · 梁惠王上》</span></span><span>行仁政而<mark>王</mark>，莫之能御也。 <span class="author"> 《孟子 · 公孙丑上》</span></span><span>周不法 商， 夏不法 虞，三代异势，而皆可以<mark>王</mark>。 <span class="author"> 《商君书》</span></span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>be emperor;</span></p><p class="explain"><span class="no">3.</span>胜过。</p><p class="extra quotes"><label>引证 <em class="sr-only">：</em></label><span>常季曰：“彼兀者也，而<mark>王</mark>先生，其与庸亦远矣。” <span class="author"> 《庄子》</span></span></p><p class="extra en"><label>英文 <em class="sr-only">：</em></label><span>surpass;</span></p><p class="explain"><span class="no">4.</span>另见 wáng。</p></div></div></div></div><div class="sticky-events--sentinel sticky-events--sentinel-bottom" style="left: 0px; position: absolute; right: 0px; visibility: hidden; bottom: 51px; height: 38px;"></div></div></div>'''

    # 提取意思信息
    yisi_data = extract_yisi_from_html(test_html)

    print("意思信息提取测试：")
    print("=" * 60)
    print(json.dumps(yisi_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_extract_yisi()