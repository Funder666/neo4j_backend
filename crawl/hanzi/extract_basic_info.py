import re
import json
from bs4 import BeautifulSoup


def extract_basic_info(html_content):
    """
    从HTML片段中提取基本信息，返回JSON格式数据
    针对data-id="基本信息"板块进行解析
    """
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


def test_extract_basic_info():
    """
    测试函数，使用提供的HTML片段
    """
    # 测试HTML片段
    html_fragment = '''<div class="card pb-3" data-id="基本信息"><div class="zi-header mb-3"><div class="zi-icon"><div class="icon"></div><div class="zi-writer-container" id="ziWriter" data-play="false"><svg width="118" height="118"><defs><clipPath id="mask-1"><path d="M 528 646 Q 601 659 678 670 Q 739 680 749 689 Q 761 698 755 709 Q 748 725 711 735 Q 672 745 579 716 Q 444 685 307 677 Q 261 673 293 649 Q 341 621 432 632 Q 450 635 472 638 L 528 646 Z"></path></clipPath><clipPath id="mask-2"><path d="M 539 380 Q 707 411 713 416 Q 723 425 719 434 Q 712 447 679 458 Q 645 465 610 453 Q 576 443 541 434 L 490 423 Q 421 410 341 405 Q 299 401 328 380 Q 373 355 455 367 Q 471 370 489 372 L 539 380 Z"></path></clipPath><clipPath id="mask-3"><path d="M 533 159 Q 536 277 539 380 L 541 434 Q 542 548 548 600 Q 557 627 529 645 L 528 646 C 505 665 463 666 472 638 Q 487 602 491 498 Q 490 468 490 423 L 489 372 Q 488 285 485 154 C 484 124 532 129 533 159 Z"></path></clipPath><clipPath id="mask-4"><path d="M 520 106 Q 574 107 626 112 Q 776 124 907 105 Q 934 102 940 111 Q 950 127 936 140 Q 903 171 855 195 Q 839 202 810 193 Q 740 180 668 171 Q 587 165 533 159 L 485 154 Q 361 145 299 138 Q 229 128 125 130 Q 109 130 108 117 Q 107 104 127 87 Q 146 72 181 58 Q 193 54 213 62 Q 231 68 304 78 Q 401 97 520 106 Z"></path></clipPath><clipPath id="mask-5"><path d="M 528 646 Q 601 659 678 670 Q 739 680 749 689 Q 761 698 755 709 Q 748 725 711 735 Q 672 745 579 716 Q 444 685 307 677 Q 261 673 293 649 Q 341 621 432 632 Q 450 635 472 638 L 528 646 Z"></path></clipPath><clipPath id="mask-6"><path d="M 539 380 Q 707 411 713 416 Q 723 425 719 434 Q 712 447 679 458 Q 645 465 610 453 Q 576 443 541 434 L 490 423 Q 421 410 341 405 Q 299 401 328 380 Q 373 355 455 367 Q 471 370 489 372 L 539 380 Z"></path></clipPath><clipPath id="mask-7"><path d="M 533 159 Q 536 277 539 380 L 541 434 Q 542 548 548 600 Q 557 627 529 645 L 528 646 C 505 665 463 666 472 638 Q 487 602 491 498 Q 490 468 490 423 L 489 372 Q 488 285 485 154 C 484 124 532 129 533 159 Z"></path></clipPath><clipPath id="mask-8"><path d="M 520 106 Q 574 107 626 112 Q 776 124 907 105 Q 934 102 940 111 Q 950 127 936 140 Q 903 171 855 195 Q 839 202 810 193 Q 740 180 668 171 Q 587 165 533 159 L 485 154 Q 361 145 299 138 Q 229 128 125 130 Q 109 130 108 117 Q 107 104 127 87 Q 146 72 181 58 Q 193 54 213 62 Q 231 68 304 78 Q 401 97 520 106 Z"></path></clipPath><clipPath id="mask-9"><path d="M 528 646 Q 601 659 678 670 Q 739 680 749 689 Q 761 698 755 709 Q 748 725 711 735 Q 672 745 579 716 Q 444 685 307 677 Q 261 673 293 649 Q 341 621 432 632 Q 450 635 472 638 L 528 646 Z"></path></clipPath><clipPath id="mask-10"><path d="M 539 380 Q 707 411 713 416 Q 723 425 719 434 Q 712 447 679 458 Q 645 465 610 453 Q 576 443 541 434 L 490 423 Q 421 410 341 405 Q 299 401 328 380 Q 373 355 455 367 Q 471 370 489 372 L 539 380 Z"></path></clipPath><clipPath id="mask-11"><path d="M 533 159 Q 536 277 539 380 L 541 434 Q 542 548 548 600 Q 557 627 529 645 L 528 646 C 505 665 463 666 472 638 Q 487 602 491 498 Q 490 468 490 423 L 489 372 Q 488 285 485 154 C 484 124 532 129 533 159 Z"></path></clipPath><clipPath id="mask-12"><path d="M 520 106 Q 574 107 626 112 Q 776 124 907 105 Q 934 102 940 111 Q 950 127 936 140 Q 903 171 855 195 Q 839 202 810 193 Q 740 180 668 171 Q 587 165 533 159 L 485 154 Q 361 145 299 138 Q 229 128 125 130 Q 109 130 108 117 Q 107 104 127 87 Q 146 72 181 58 Q 193 54 213 62 Q 231 68 304 78 Q 401 97 520 106 Z"></path></clipPath></defs><g transform="translate(2, 102.1953125) scale(0.111328125, -0.111328125)"><g style="opacity: 1;"><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-1&quot;)" d="M 198.8 688.6 L 329 657 L 385 655 L 675 704 L 742 702" stroke="rgba(221,221,221,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="551.1319241398062,551.1319241398062" style="opacity: 1; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-2&quot;)" d="M 233.2 414.8 L 364 387 L 424 387 L 548 407 L 647 431 L 706 428" stroke="rgba(221,221,221,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="480.2805863607922,480.2805863607922" style="opacity: 1; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-3&quot;)" d="M 397.9 694.5 L 515 610 L 516 575 L 510 185 L 490 163" stroke="rgba(221,221,221,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="599.1997780324895,599.1997780324895" style="opacity: 1; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-4&quot;)" d="M 30.6 156.6 L 158 100 L 196 94 L 403 122 L 837 156 L 926 123" stroke="rgba(221,221,221,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="917.002115098303,917.002115098303" style="opacity: 1; stroke-dashoffset: 0;"></path></g><g style="opacity: 1;"><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-5&quot;)" d="M 198.8 688.6 L 329 657 L 385 655 L 675 704 L 742 702" stroke="rgba(255,0,0,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="551.1319241398062,551.1319241398062" style="opacity: 1; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-6&quot;)" d="M 233.2 414.8 L 364 387 L 424 387 L 548 407 L 647 431 L 706 428" stroke="rgba(255,0,0,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="480.2805863607922,480.2805863607922" style="opacity: 1; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-7&quot;)" d="M 397.9 694.5 L 515 610 L 516 575 L 510 185 L 490 163" stroke="rgba(255,0,0,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="599.1997780324895,599.1997780324895" style="opacity: 1; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-8&quot;)" d="M 30.6 156.6 L 158 100 L 196 94 L 403 122 L 837 156 L 926 123" stroke="rgba(255,0,0,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="917.002115098303,917.002115098303" style="opacity: 1; stroke-dashoffset: 0;"></path></g><g style="opacity: 1;"><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-9&quot;)" d="M 198.8 688.6 L 329 657 L 385 655 L 675 704 L 742 702" stroke="rgba(170,170,255,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="551.1319241398062,551.1319241398062" style="opacity: 0; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-10&quot;)" d="M 233.2 414.8 L 364 387 L 424 387 L 548 407 L 647 431 L 706 428" stroke="rgba(170,170,255,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="480.2805863607922,480.2805863607922" style="opacity: 0; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-11&quot;)" d="M 397.9 694.5 L 515 610 L 516 575 L 510 185 L 490 163" stroke="rgba(170,170,255,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="599.1997780324895,599.1997780324895" style="opacity: 0; stroke-dashoffset: 0;"></path><path clip-path="url(&quot;https://www.hanyuguoxue.com/zidian/zi-29579#mask-12&quot;)" d="M 30.6 156.6 L 158 100 L 196 94 L 403 122 L 837 156 L 926 123" stroke="rgba(170,170,255,1)" stroke-width="200" fill="none" stroke-linecap="round" stroke-linejoin="miter" stroke-dasharray="917.002115098303,917.002115098303" style="opacity: 0; stroke-dashoffset: 0;"></path></g></g></svg></div><div class="zi-writer-btn" data-times="1" id="ziAnimate"></div><div class="zi-control" id="ziWriterControl"><button class="btn">播放</button><button class="btn">全屏</button></div></div><div class="zi-title"><div class="zi-title-main"><h2>王</h2><span class="zi-title-copy badge badge-primary copy" data-clipboard-text="王" data-toggle="tooltip" title="" data-original-title="复制">复制</span></div><div class="pinyin"><p><span class="voice" data-voice="wang2.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"> <em class="py">wáng</em> <em class="zy">ㄨㄤˊ</em> </span> <span class="voice" data-voice="wang4.mp3"><img width="20" height="20" src="//static.hanyuguoxue.com/assets/images/volume.png"> <em class="py">wàng</em> <em class="zy">ㄨㄤˋ</em> </span></p></div><div class="zi-title-extra"><span>王部</span><span>共4画</span><span>独体字</span><span class="unicode">U+738B</span><span>CJK 基本汉字</span></div><div class="zi-tags"><a class="badge badge-primary" href="/zidian/zuichangyongzi" title="最常用字">最常用字</a><a class="badge badge-primary" href="/zidian/guifanhanzi-1" title="一级汉字">一级汉字</a><a class="badge badge-primary" href="/zidian/changyongzi-2500" title="常用字">常用字</a><a class="badge badge-primary" href="/zidian/tongyongzi" title="通用字">通用字</a><a class="badge badge-primary" href="/zidian/dutizidaquan" title="独体字">独体字</a></div><div class="zi-category">汉语字典</div></div></div><div class="zi-tab"><ul><li class="active"><a href="/zidian/zi-29579">汉语字典</a></li><li><a href="/kangxi/zi-29579">康熙字典</a></li><li><a href="/shuowen/zi-29579">说文解字</a></li><li><a href="/zuci/zi-29579">组词</a></li></ul></div><div class="zi-attrs"><div class="zi-attrs-list"><p><label>部首</label> <span> <a class="primary" href="/zidian/bushou-29579" title="部首王的汉字">王部</a> </span></p><p><label>总笔画</label> <span> <a class="primary" href="/zidian/bihua-4" title="总笔画4的汉字">4画</a> </span></p><p><label>结构</label> <span>独体字</span></p><p><label>造字法</label> <span>会意字</span></p><p><label>五行</label> <span>土</span></p><p><label>五笔</label> <span> GGGG </span></p><p><label>仓颉</label> <span> MG </span></p><p><label>郑码</label> <span> CA </span></p><p><label>四角</label> <span> 10104</span></p><p><label>中文电码</label> <span>3769</span></p><p><label>区位码</label> <span>4585</span></p><p style="flex-grow:1"><label>统一码</label> <span>U+738B</span></p><p class="bishun"><label>笔画</label> <span> <em>1121</em> 横、横、竖、横 </span></p><p class="w-100"><label>异体字</label> <span class="font-18 zi-font" style="margin-left:8px!important"> <a class="primary" href="/zidian/zi-29577"> 玉 </a> 、 <a class="primary" href="/zidian/zi-132731"> 𠙻 </a> 、 <a class="primary" href="/zidian/zi-134198"> 𠰶 </a> 、 <a class="primary" href="/zidian/zi-138084"> 𡭤 </a> 、 <a class="primary" href="/zidian/zi-149767"> 𤤇 </a> 、 <a class="primary" href="/zidian/zi-153421"> 𥝍 </a> </span></p></div></div></div>'''

    # 提取基本信息
    basic_info = extract_basic_info(html_fragment)

    # 打印JSON格式的结果
    print("基本信息 (JSON格式):")
    print(json.dumps(basic_info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_extract_basic_info()