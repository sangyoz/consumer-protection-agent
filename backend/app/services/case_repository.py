"""Relational persistence boundary. API/Agent still consume the same case dict.

Business collections are individual SQL rows; only unstructured AI output and
extension fields use JSON. Updates and child deletions share one transaction.
"""
from copy import deepcopy

from app.database import (CaseRecord, Message, Material, EvidenceItem, CaseStep,
                          ProgressRecord, CaseEvent, CasePlan, CaseAnalysis)

CASE_FIELDS = {name: name for name in ('id', 'title', 'summary', 'merchant', 'amount', 'goal', 'platform', 'product', 'payee', 'stage')}
CASE_FIELDS.update(tradeTime='trade_time', creditCode='credit_code', createdAt='created_at', updatedAt='updated_at')
STATE_FIELDS = dict(analysis='analysis', agent_state='agent_state', complaint='complaint',
                    complaintAttachments='complaint_attachments', goalPlan='goal_plan', resolution='resolution')
PLAN_FIELDS = {name: name for name in ('version', 'locked', 'engine', 'reason', 'current_step_id')}
PLAN_FIELDS['updated_at'] = 'updated_at'
COLLECTIONS = {
    'messages': ('messages', Message, dict(id='id', role='role', content='content', createdAt='created_at')),
    'materials': ('materials', Material, dict(id='id', name='name', size='size', status='status', storageName='storage_name', kind='kind', source='source', uploadedAt='uploaded_at')),
    'evidence_checklist': ('evidence_items', EvidenceItem, dict(key='key', label='label', status='status', note='note', content_verified='content_verified')),
    'followups': ('progress_records', ProgressRecord, dict(id='id', step_id='step_id', note='note', stage='stage', status='status', confirmed='confirmed', channel='channel', caseNo='case_no', acceptStatus='accept_status', deadline='deadline', createdAt='created_at')),
    'timeline': ('events', CaseEvent, dict(id='id', text='text', createdAt='created_at')),
}
STEP_FIELDS = {name: name for name in ('id', 'type', 'title', 'status', 'reason', 'completion_condition', 'note', 'feedback_at')}


def write_fields(row, document, mapping, excluded=()):
    row.field_names = list(document)
    row.extra_data = deepcopy({key: value for key, value in document.items() if key not in mapping and key not in excluded})
    for key, attribute in mapping.items():
        setattr(row, attribute, deepcopy(document.get(key)))


def read_fields(row, mapping):
    document = deepcopy(row.extra_data or {})
    for key, attribute in mapping.items():
        if key in (row.field_names or []):
            document[key] = deepcopy(getattr(row, attribute))
    return document


def sync_rows(record, attribute, model, documents, mapping):
    previous = {row.position: row for row in getattr(record, attribute)}
    rows = []
    for position, document in enumerate(documents or []):
        row = previous.get(position)
        if row is None:
            row = model(position=position)
        write_fields(row, document, mapping)
        rows.append(row)
    setattr(record, attribute, rows)


def store_case(record, case):
    write_fields(record, case, CASE_FIELDS, {
        *[key for key in COLLECTIONS if isinstance(case.get(key), list)], *STATE_FIELDS, 'plan'})
    for key, (attribute, model, mapping) in COLLECTIONS.items():
        sync_rows(record, attribute, model, case.get(key), mapping)
    state = {key: case[key] for key in STATE_FIELDS if key in case}
    if state:
        if record.analysis_record is None:
            record.analysis_record = CaseAnalysis()
        write_fields(record.analysis_record, state, STATE_FIELDS)
    else:
        record.analysis_record = None
    plan = case.get('plan')
    if plan is not None:
        if record.plan is None:
            record.plan = CasePlan()
        write_fields(record.plan, plan, PLAN_FIELDS, {'steps'} if isinstance(plan.get('steps'), list) else ())
        sync_rows(record, 'steps', CaseStep, plan.get('steps'), STEP_FIELDS)
    else:
        record.plan = None
        record.steps = []
    return record


def load_case(record):
    case = read_fields(record, CASE_FIELDS)
    for key, (attribute, _, mapping) in COLLECTIONS.items():
        if key in (record.field_names or []):
            if key not in case:
                case[key] = [read_fields(row, mapping) for row in getattr(record, attribute)]
    if record.analysis_record:
        case.update(read_fields(record.analysis_record, STATE_FIELDS))
    if 'plan' in (record.field_names or []):
        if record.plan is None:
            case['plan'] = None
        else:
            case['plan'] = read_fields(record.plan, PLAN_FIELDS)
            if 'steps' in (record.plan.field_names or []) and 'steps' not in case['plan']:
                case['plan']['steps'] = [read_fields(row, STEP_FIELDS) for row in record.steps]
    return case
