"""确定性规则与枚举常量（不含模型推理）。

后续 Agent 负责语义判断；本模块只提供前后端共用的类型、标签和材料缺口核对规则。
"""

from pathlib import Path

MATERIAL_KINDS = {
    'order': '订单/付款凭证',
    'contract': '合同/宣传页',
    'photo': '问题照片/视频',
    'chat': '沟通记录',
    'other': '其他材料',
}

MATERIAL_SOURCES = {
    'user': '用户上传',
    'extracted': '文件提取',
    'inferred': 'AI 推断',
}

# 第一阶段（网购质量与退款纠纷）建议具备的材料；后续按纠纷类型扩展。
REQUIRED_MATERIALS = [
    ('order', '订单或付款凭证'),
    ('photo', '问题照片或视频'),
    ('chat', '与商家沟通记录'),
]

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg'}


def kind_from_suffix(filename: str) -> str:
    suffix = Path(filename or '').suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return 'photo'
    return 'other'


def missing_materials(materials: list[dict]) -> list[dict]:
    """按必备材料清单核对已上传材料，返回缺失项。"""
    uploaded = {m.get('kind') for m in materials}
    return [{'kind': kind, 'label': label} for kind, label in REQUIRED_MATERIALS if kind not in uploaded]


# 投诉渠道规则（确定性配置；推荐理由与适用性判断后续可由 Agent 补充）。
CHANNELS = [
    {
        'key': 'platform',
        'name': '交易平台售后',
        'category': '商业平台投诉',
        'scope': '网购订单优先在平台内申请售后或平台介入，处理速度通常较快。',
        'materials': ['order', 'chat'],
    },
    {
        'key': 'market_12315',
        'name': '12315 平台 / 市场监管部门',
        'category': '行政投诉',
        'scope': '商家拒绝处理、拖延推诿或涉嫌违法违规时，向市场监管部门投诉。',
        'materials': ['order', 'photo', 'chat'],
    },
    {
        'key': 'hotline_12345',
        'name': '12345 政务服务便民热线',
        'category': '行政投诉',
        'scope': '需要协调属地部门处理、或不清楚对应监管部门时拨打。',
        'materials': ['order'],
    },
    {
        'key': 'consumer_assoc',
        'name': '消费者协会调解',
        'category': '调解渠道',
        'scope': '自愿向消协申请调解，适合希望第三方居中协商的纠纷。',
        'materials': ['order', 'chat'],
    },
    {
        'key': 'industry',
        'name': '行业主管部门',
        'category': '行政投诉',
        'scope': '食品、预付卡、服务等特定行业，向对应行业监管部门反映。',
        'materials': ['order', 'contract'],
    },
    {
        'key': 'justice',
        'name': '仲裁或人民法院',
        'category': '司法救济',
        'scope': '争议较大、金额较高，或其他渠道无果后的司法途径。',
        'materials': ['order', 'contract', 'chat'],
    },
]

# 投诉受理状态（跟进阶段使用）。
ACCEPT_STATUSES = {
    'pending': '待受理',
    'accepted': '已受理',
    'supplement': '需补充材料',
    'rejected': '未受理',
    'contacted': '商家已联系',
    'resolved': '已履行',
}
