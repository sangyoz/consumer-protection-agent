"""Evidence inventory; file names are hints, never proof of file contents."""
DEFINITIONS = {
    'transaction': ('订单、合同或服务协议', ('订单', '合同', 'order', 'contract')),
    'payment': ('付款凭证或交易记录', ('付款', '支付', '收据', 'payment', 'receipt')),
    'issue': ('与争议对应的问题记录或服务履约记录', ('照片', '视频', '检测', '停业', 'photo', 'video')),
    'communication': ('与商家的沟通记录', ('聊天', '沟通', 'chat')),
}


def assess(case: dict, merchant_reply: str = '') -> list[dict]:
    inventory = []
    declared = {row['key']: row for row in case.get('evidence_checklist', []) if row.get('key') in DEFINITIONS}
    for key, (label, hints) in DEFINITIONS.items():
        materials = [row['id'] for row in case.get('materials', []) if row.get('status') == 'uploaded'
                     and any(hint in row.get('name', '').lower() for hint in hints)]
        status = 'uploaded_unverified' if materials else 'missing'
        if key == 'communication' and (merchant_reply or any(message.get('role') == 'merchant' for message in case.get('messages', []))):
            status = 'user_provided'
        declaration = declared.get(key)
        note = ''
        if declaration:
            # These entries are written by the explicit evidence confirmation endpoint.
            status = declaration['status']
            note = declaration.get('note', '')
        inventory.append({'key': key, 'item': label, 'status': status, 'material_ids': materials,
                          'note': note, 'required': key in ('transaction', 'payment'),
                          'content_verified': False})
    return inventory


def needs_evidence(inventory: list[dict]) -> bool:
    return any(row['required'] and row['status'] not in ('user_confirmed', 'user_provided') for row in inventory)
