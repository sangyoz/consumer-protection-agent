"""Bounded decide → tool → observation → draft → audit/correct LangGraph."""
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from ..services import agent, evidence, retrieval


class AgentState(TypedDict):
    operation: Literal['analysis', 'reply', 'complaint']
    case: dict
    merchant_reply: str
    evidence_checklist: list[dict]
    merchant_claim_checks: list[dict]
    decision: dict
    retrieval: dict
    executed_tools: list[str]
    tool_rounds: int
    draft: dict
    audit: dict
    correction_count: int
    correction_history: list[dict]
    trace: list[str]
    result: dict


def assess_evidence(state: AgentState) -> dict:
    return {'evidence_checklist': evidence.assess(state['case'], state['merchant_reply']),
            'merchant_claim_checks': retrieval.check_merchant_claims(state['merchant_reply']),
            'trace': state['trace'] + ['assess_evidence']}


def decide(state: AgentState) -> dict:
    decision = agent.decide(state['operation'], state['case'], state['merchant_reply'],
                            state['evidence_checklist'], state['retrieval'], state['executed_tools'])
    # Opponent citation claims always require local lookup, even while the user
    # is still collecting evidence. Model discretion cannot skip this check.
    if state['merchant_claim_checks'] and 'search_local_law' not in state['executed_tools']:
        if 'search_local_law' not in decision['tools']:
            decision['tools'].append('search_local_law')
    return {'decision': decision, 'trace': state['trace'] + ['decide']}


def route_decision(state: AgentState) -> str:
    if state['decision']['tools'] and state['tool_rounds'] < 2:
        return 'retrieve_context'
    return state['decision']['action']


def retrieve_context(state: AgentState) -> dict:
    tools = state['decision']['tools']
    context = retrieval.search(state['decision']['query'], tools)
    old = state['retrieval']
    if 'search_local_law' not in tools:
        context['laws'] = old['laws']
        for key in ('law_library', 'law_search_mode'):
            context['status'][key] = old['status'][key]
    if 'search_web_experience' not in tools:
        context['cases'] = old['cases']
        context['status']['case_search'] = old['status']['case_search']
    context['merchant_claim_checks'] = state['merchant_claim_checks']
    return {'retrieval': context, 'executed_tools': state['executed_tools'] + tools,
            'tool_rounds': state['tool_rounds'] + 1, 'trace': state['trace'] + ['retrieve_context']}


def draft(state: AgentState, action: str | None = None) -> dict:
    selected_action = action or state['decision']['action']
    result = agent.generate(state['operation'], state['case'], state['merchant_reply'],
                            state['evidence_checklist'], {**state['retrieval'], 'merchant_claim_checks': state['merchant_claim_checks']},
                            state['audit'].get('feedback', ''), {**state['decision'], 'action': selected_action})
    return {'draft': result, 'trace': state['trace'] + [selected_action]}


def strategy_node(action: str):
    def run(state: AgentState) -> dict:
        return draft(state, action)
    run.__name__ = action
    return run


def audit_citations(state: AgentState) -> dict:
    result = state['draft']
    # Audit every model-generated textual field, including category and missing.
    text = '\n'.join(str(result.get(key, '')) for key in ('category', 'missing', 'rights', 'strategy', 'script', 'reply', 'complaint'))
    audit = retrieval.audit_citations(text, state['retrieval']['laws'], result.get('citations', []))
    return {'audit': audit, 'trace': state['trace'] + ['audit_citations']}


def route_after_audit(state: AgentState) -> str:
    if state['audit']['valid']:
        return 'finish'
    return 'correct' if state['correction_count'] < 1 else 'safe_fallback'


def correct(state: AgentState) -> dict:
    return {'correction_count': state['correction_count'] + 1,
            'correction_history': state['correction_history'] + [state['audit']],
            'trace': state['trace'] + ['correct']}


def safe_fallback(state: AgentState) -> dict:
    result = agent.fallback_draft(state['operation'], state['evidence_checklist'],
                                  state['decision']['action'], 'citation_audit_failed')
    # No rejected model output survives. Preserve failure diagnostics separately.
    return {'draft': result, 'correction_history': state['correction_history'] + [state['audit']],
            'audit': {'valid': True, 'invalid_citations': [], 'used_law_ids': [], 'feedback': '',
                      'scope': 'source_identity_and_quote_only', 'safe_fallback': True},
            'trace': state['trace'] + ['safe_fallback']}


def finish(state: AgentState) -> dict:
    result = dict(state['draft'])
    used = set(state['audit']['used_law_ids'])
    laws = [row for row in state['retrieval']['laws'] if row['id'] in used]
    quotes = {row['law_id']: row['quote'] for row in result.get('citations', [])}
    claim_check_text = retrieval.format_merchant_checks(state['merchant_claim_checks'])
    if claim_check_text:
        result['reply'] = claim_check_text + '\n\n' + result.get('reply', '')
    sources = [{'law_id': row['id'], 'citation': f"《{row['law_name']}》第{row['article']}条",
                'quote': quotes.get(row['id'], row['content']), 'source': row['source'],
                'effective_from': row['effective_from'], 'reviewed_at': row['reviewed_at']} for row in laws]
    explanation = '引用身份与原文已匹配本地维护的法律库；是否适用于本案仍需核对。' if sources else '本轮没有可引用的法律条文，请先补充交易事实和证据。'
    if sources:
        explanation += '\n\n' + '\n\n'.join(f"{row['citation']}\n原文：{row['quote']}\n来源：{row['source']}" for row in sources)
    if sources:
        source_text = '\n\n参考原文与来源：\n' + '\n'.join(f"{row['citation']}：{row['quote']}\n{row['source']}" for row in sources)
        result['reply'] += source_text
        if result['complaint']:
            result['complaint'] += source_text
    result.update(summary=state['case'].get('summary', ''), evidence_checklist=state['evidence_checklist'],
                  merchant_claim_checks=state['merchant_claim_checks'],
                  decision=state['decision'], executed_tools=state['executed_tools'],
                  retrieval=state['retrieval']['status'],
                  retrieved_cases=state['retrieval']['cases'],
                  audit={**state['audit'], 'correction_attempts': state['correction_count'],
                         'correction_history': state['correction_history']},
                  trace=state['trace'] + ['finish'],
                  legal={'name': '法条引用来源核验' if sources else '暂无法条引用',
                         'explanation': explanation, 'source': sources[0]['source'] if sources else '',
                         'citations': sources, 'verified': bool(sources), 'applicability_verified': False})
    return {'result': result}


builder = StateGraph(AgentState)
for name, function in [('assess_evidence', assess_evidence), ('decide', decide),
                       ('retrieve_context', retrieve_context), ('audit_citations', audit_citations),
                       ('correct', correct), ('safe_fallback', safe_fallback), ('finish', finish)]:
    builder.add_node(name, function)
for action in ('clarify_user', 'collect_evidence', 'negotiate', 'escalate', 'complaint'):
    builder.add_node(action, strategy_node(action))
    builder.add_edge(action, 'audit_citations')
builder.add_edge(START, 'assess_evidence')
builder.add_edge('assess_evidence', 'decide')
builder.add_conditional_edges('decide', route_decision,
                              {name: name for name in ('retrieve_context', 'clarify_user', 'collect_evidence', 'negotiate', 'escalate', 'complaint')})
builder.add_edge('retrieve_context', 'decide')
builder.add_conditional_edges('audit_citations', route_after_audit,
                              {name: name for name in ('correct', 'safe_fallback', 'finish')})
builder.add_conditional_edges('correct', lambda state: state['decision']['action'],
                              {name: name for name in ('clarify_user', 'collect_evidence', 'negotiate', 'escalate', 'complaint')})
builder.add_edge('safe_fallback', 'finish')
builder.add_edge('finish', END)
workflow = builder.compile()


def run_case(operation: Literal['analysis', 'reply', 'complaint'], case: dict, merchant_reply: str = '') -> dict:
    initial = {'operation': operation, 'case': case, 'merchant_reply': merchant_reply,
               'evidence_checklist': [], 'merchant_claim_checks': [], 'decision': {},
               'retrieval': {'laws': [], 'cases': [], 'status': {'law_library': 'not_requested', 'law_search_mode': 'none', 'case_search': 'not_requested'}},
               'executed_tools': [], 'tool_rounds': 0, 'draft': {}, 'result': {},
               'audit': {'valid': True, 'feedback': ''}, 'correction_count': 0,
               'correction_history': [], 'trace': []}
    return workflow.invoke(initial, config={'recursion_limit': 30})['result']


def run_analysis(case: dict) -> dict:
    return run_case('analysis', case)


def run_reply(case: dict, merchant_reply: str) -> str:
    return run_case('reply', case, merchant_reply)['reply']


def run_complaint(case: dict) -> dict:
    return run_case('complaint', case)
