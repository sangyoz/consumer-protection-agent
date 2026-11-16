"""规则字段提取：只抽取能定位到原文的字段，不做推断。

设计约束：
1. 每个字段都带 evidence（原文片段与起止位置），回指不上的一律不采用。
2. 抽不到的字段进入 missing，由用户自己补，不猜。
3. 后续接入模型时替换本模块实现即可，返回结构保持不变。
4. 前端 domain/extract.js 是同一套规则的镜像，修改时两份需同步。
"""

import re
from datetime import date, timedelta

PLATFORMS = (
    '苏宁易购', '拼多多', '唯品会', '小红书', '淘宝', '天猫', '京东', '抖音',
    '快手', '美团', '饿了么', '闲鱼', '苏宁', '线下门店', '实体店', '超市', '商场',
)

GOAL_RULES = (
    (('退货退款', '退款', '退钱', '退费', '返还', '不退', '不给退', '拒绝退'), '退货退款'),
    (('换货', '更换', '换个'), '换货'),
    (('维修', '修理', '修好'), '维修'),
    (('赔偿', '赔付', '补偿'), '赔偿'),
    (('补发', '重发'), '补发'),
)

MERCHANT_SUFFIXES = ('旗舰店', '专卖店', '专营店', '商店', '店铺', '公司', '健身房', '超市', '餐厅', '酒店', '商城', '门店', '店')
MERCHANT_STOP = {'商家', '店家', '客服', '平台', '卖家', '对方', '公司', '门店', '实体店', '线下门店'}
MERCHANT_VERB_PREFIX = ('联系', '咨询', '询问', '投诉', '找到', '跟', '和', '向', '这家', '那家', '该')

PRODUCT_VERBS = ('购买了', '购买', '买了', '买', '入手了', '入手', '下单了', '下单', '订购了', '订购', '点了', '订了', '叫了')
PRODUCT_NOISE = ('右侧', '左侧', '这边', '那边', '收到', '发现', '结果', '但是', '但', '可是', '却', '一直', '现在', '坏了', '有问题', '无法', '不能', '没有声音', '无声音', '没声音')

REQUIRED_FIELDS = (
    ('merchant', '商家名称'),
    ('amount', '交易金额'),
    ('product', '商品/服务'),
    ('tradeTime', '交易时间'),
)

AMOUNT_PATTERN = re.compile(r'(?:¥|￥)\s*(\d[\d,]*(?:\.\d{1,2})?)|(\d[\d,]*(?:\.\d{1,2})?)\s*(?:元|块钱|块)')
FULL_DATE = re.compile(r'(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*[日号]?')
SHORT_DATE = re.compile(r'(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]')
CREDIT_CODE = re.compile(r'(?<![0-9A-Z])([0-9A-HJ-NPQRTUWXY]{18})(?![0-9A-Z])')


def _entry(field, value, snippet, start, end):
    return {'field': field, 'value': value, 'snippet': snippet, 'start': start, 'end': end}


def extract_amount(text):
    for match in AMOUNT_PATTERN.finditer(text):
        raw = (match.group(1) or match.group(2)).replace(',', '')
        try:
            value = float(raw)
        except ValueError:
            continue
        if 0 < value <= 100000000:
            return value, match
    return None


def extract_platform(text):
    hits = [(text.find(name), -len(name), name) for name in PLATFORMS if text.find(name) >= 0]
    if not hits:
        return None
    hits.sort()
    index, _, name = hits[0]
    return name, index, index + len(name)


def extract_product(text):
    for verb in PRODUCT_VERBS:
        index = text.find(verb)
        if index < 0:
            continue
        start = index + len(verb)
        head = re.split(r'[，,。；;！!？?\n]', text[start:start + 40])[0]
        head = re.sub(r'^[了]?(?:一|两|三|几|半)?[个台部双件张只瓶盒套份]?', '', head)
        for noise in PRODUCT_NOISE:
            if noise in head:
                head = head.split(noise)[0]
        value = head.strip('，, 。；、的')
        if not 1 <= len(value) <= 20:
            continue
        position = text.find(value, start)
        if position < 0:
            position = start
        return value, position, position + len(value)
    return None


def extract_goal(text):
    best = None
    for keywords, goal in GOAL_RULES:
        for keyword in keywords:
            index = text.find(keyword)
            if index >= 0 and (best is None or index < best[0]):
                best = (index, goal, keyword)
    if best is None:
        return None
    index, goal, keyword = best
    return goal, index, index + len(keyword)


def extract_merchant(text):
    for match in re.finditer(r'([\u4e00-\u9fa5A-Za-z0-9]{2,20}(?:' + '|'.join(MERCHANT_SUFFIXES) + '))', text):
        name = match.group(1)
        name = re.sub(r'^(?:这家|那家|该|这个|那个|一家)', '', name)
        if len(name) < 3 or name in MERCHANT_STOP:
            continue
        if name.startswith(MERCHANT_VERB_PREFIX):
            continue
        offset = max(match.group(1).find(name), 0)
        start = match.start() + offset
        return name, start, start + len(name)
    return None


def extract_trade_time(text, today=None):
    today = today or date.today()
    match = FULL_DATE.search(text)
    if match:
        try:
            value = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            return value.isoformat(), match.start(), match.end()
        except ValueError:
            pass
    match = SHORT_DATE.search(text)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        for year in (today.year, today.year - 1):
            try:
                value = date(year, month, day)
            except ValueError:
                continue
            if value <= today:
                return value.isoformat(), match.start(), match.end()
    relative = {'大前天': -3, '前天': -2, '昨天': -1, '今天': 0, '上周': -7, '上个月': -30}
    for word, offset in relative.items():
        index = text.find(word)
        if index >= 0:
            return (today + timedelta(days=offset)).isoformat(), index, index + len(word)
    return None


def extract(text, today=None):
    text = text or ''
    fields, evidence = {}, []

    amount = extract_amount(text)
    if amount:
        value, match = amount
        fields['amount'] = int(value) if float(value).is_integer() else value
        evidence.append(_entry('amount', fields['amount'], match.group(0).strip(), match.start(), match.end()))

    platform = extract_platform(text)
    if platform:
        name, start, end = platform
        fields['platform'] = name
        evidence.append(_entry('platform', name, text[start:end], start, end))

    product = extract_product(text)
    if product:
        value, start, end = product
        fields['product'] = value
        evidence.append(_entry('product', value, text[start:end], start, end))

    goal = extract_goal(text)
    if goal:
        value, start, end = goal
        fields['goal'] = value
        evidence.append(_entry('goal', value, text[start:end], start, end))

    merchant = extract_merchant(text)
    if merchant:
        value, start, end = merchant
        fields['merchant'] = value
        evidence.append(_entry('merchant', value, text[start:end], start, end))

    trade_time = extract_trade_time(text, today)
    if trade_time:
        value, start, end = trade_time
        fields['tradeTime'] = value
        evidence.append(_entry('tradeTime', value, text[start:end], start, end))

    credit = CREDIT_CODE.search(text)
    if credit:
        fields['creditCode'] = credit.group(1)
        evidence.append(_entry('creditCode', credit.group(1), credit.group(0), credit.start(), credit.end()))

    missing = [{'field': field, 'label': label} for field, label in REQUIRED_FIELDS if field not in fields]
    return {'fields': fields, 'evidence': evidence, 'missing': missing}
