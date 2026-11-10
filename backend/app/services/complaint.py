"""只整理本案已有事实；不调用任何外部投诉提交接口。"""


def generate(case: dict) -> str:
    replies = '\n'.join(message['content'] for message in case['messages'] if message['role'] == 'merchant') or '待补充商家沟通记录'
    materials = '\n'.join('· ' + material['name'] for material in case['materials']) or '待补充订单、付款凭证和相关材料'
    return (
        f'【投诉材料草稿 · 待用户核对】\n\n投诉对象：{case["merchant"] or "待补充经营主体"}\n'
        f'交易金额：{str(case["amount"]) + " 元" if case["amount"] else "待补充"}\n\n'
        f'纠纷经过：\n{case["summary"]}\n\n具体诉求：\n{case["goal"]}\n\n'
        f'协商记录：\n{replies}\n\n证据清单：\n{materials}\n\n'
        '法律依据：待检索并核验后补充。\n\n请核对真实事实、经营主体和附件，再选择适合的渠道提交。'
    )
