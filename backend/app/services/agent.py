"""模拟 Agent 边界。

后续在此调用 agents/workflow.py，接入 LangGraph、DeepSeek 与法律检索。
不得将本文件的模板输出视作真实模型分析或已核验的法律建议。
"""


def analyze(case: dict) -> dict:
    return {
        'summary': case['summary'],
        'category': '预付式消费纠纷' if any(w in case['summary'] for w in ['健身', '会员', '预付']) else '商品／服务消费纠纷',
        'missing': ['核对商家名称与实际收款方', '补充合同、订单及付款凭证', '确认希望解决的问题和已沟通过程'],
        'rights': '先核对交易事实、合同约定和证据，再确认可提出的退款、维修或履约诉求。当前内容仅用于展示分析页面。',
        'legal': {'name': '法律检索模块待接入', 'explanation': '正式接入后展示法律原文、通俗解释、适用条件和官方来源。当前没有已核验的法律结论。', 'source': '', 'verified': False},
        'strategy': '先说明事实和具体诉求，要求商家明确答复处理方案与时间，保留沟通记录。',
        'script': f'您好，关于{case["title"]}，{case["goal"]}。请说明处理方案、计算依据和预计完成时间。',
    }


def reply(case: dict, content: str) -> str:
    # case 参数保留完整上下文，后续传给带状态的 Agent，而非只分析单条消息。
    if any(word in content for word in ['等', '通知', '耐心']):
        concern = '对方提到了等待，需要进一步明确处理期限。'
    elif any(word in content for word in ['不退', '拒绝', '规定']):
        concern = '对方表达了拒绝处理的态度，需要核对具体理由和合同依据。'
    else:
        concern = '请核对对方是否明确回应了诉求、处理方式及完成时间。'
    return concern + '建议保留本轮记录，并要求对方给出书面方案。这是模拟分析，不构成法律判断。'
