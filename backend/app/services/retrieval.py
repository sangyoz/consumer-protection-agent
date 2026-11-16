"""Local BM25/vector retrieval, domain-restricted web search and citation audit.

The SQLite law corpus is independent of the application's SQLite/MySQL case DB.
Import is explicit: never download or invent statutes during a user request.
"""
import json
import math
import os
import re
import sqlite3
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALLOWED_CASE_HOSTS = {'tousu.sina.com.cn', 'anli.court.gov.cn'}
LAW_HOSTS = {'flk.npc.gov.cn', 'www.npc.gov.cn', 'npc.gov.cn', 'www.gov.cn'}


def _db_path() -> Path:
    value = Path(os.getenv('LAW_DB_PATH', str(BACKEND_DIR / 'legal.sqlite3')))
    return value if value.is_absolute() else BACKEND_DIR / value


def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute('''CREATE TABLE IF NOT EXISTS law_articles (
        id TEXT PRIMARY KEY, law_name TEXT NOT NULL, article TEXT NOT NULL,
        content TEXT NOT NULL, source TEXT NOT NULL, effective_from TEXT NOT NULL,
        effective_to TEXT, reviewed_at TEXT NOT NULL, UNIQUE(law_name, article, effective_from)
    )''')
    connection.execute('''CREATE TABLE IF NOT EXISTS law_embeddings (
        article_id TEXT NOT NULL, model TEXT NOT NULL, endpoint TEXT NOT NULL,
        content TEXT NOT NULL, vector TEXT NOT NULL,
        PRIMARY KEY(article_id, model, endpoint)
    )''')
    connection.commit()
    return connection


def normalize_article(value: str) -> str:
    value = str(value).strip().removeprefix('第').removesuffix('条')
    if value.isdigit():
        return str(int(value))
    digits = dict(zip('零〇一二三四五六七八九', [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]))
    units = {'十': 10, '百': 100, '千': 1000, '万': 10000}
    if not value or any(char not in digits and char not in units for char in value):
        raise ValueError('条号必须是阿拉伯数字或中文数字')
    total = number = 0
    for char in value:
        if char in digits:
            number = digits[char]
        else:
            total += (number or 1) * units[char]
            number = 0
    return str(total + number)


def _law_key(value: str) -> str:
    value = value.strip('《》 ').removeprefix('中华人民共和国')
    return {'消法': '消费者权益保护法'}.get(value, value)


def _valid_url(url: str, hosts: set[str]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == 'https' and parsed.hostname in hosts and not parsed.username and not parsed.password


def import_laws(path: str | Path) -> int:
    """Import reviewed official JSONL, transactionally, without demo law content.

Each row: id, law_name, article, content, source, effective_from,
reviewed_at, optional effective_to. Review dates record the corpus maintainer's
verification; a trusted domain alone does not prove that text is authoritative.
"""
    prepared = []
    with Path(path).open(encoding='utf-8-sig') as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            fields = ('id', 'law_name', 'article', 'content', 'source', 'effective_from', 'reviewed_at')
            if not isinstance(row, dict) or not all(isinstance(row.get(key), str) and row[key].strip() for key in fields):
                raise ValueError('法律数据缺少必填字符串字段：' + ', '.join(fields))
            if not _valid_url(row['source'], LAW_HOSTS):
                raise ValueError('法律来源须为配置的官方 HTTPS 域名')
            start = date.fromisoformat(row['effective_from'])
            reviewed = date.fromisoformat(row['reviewed_at'])
            end = date.fromisoformat(row['effective_to']) if row.get('effective_to') else None
            if reviewed > date.today() or (end and end < start):
                raise ValueError('法律生效/复核日期无效')
            prepared.append((row['id'], row['law_name'].strip('《》 '), normalize_article(row['article']),
                             row['content'], row['source'], start.isoformat(), end.isoformat() if end else None, reviewed.isoformat()))
    connection = _connect()
    try:
        with connection:
            connection.executemany('''INSERT INTO law_articles VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET law_name=excluded.law_name, article=excluded.article,
                content=excluded.content, source=excluded.source, effective_from=excluded.effective_from,
                effective_to=excluded.effective_to, reviewed_at=excluded.reviewed_at''', prepared)
    finally:
        connection.close()
    return len(prepared)


def _active_laws() -> list[dict]:
    connection = _connect()
    try:
        today = date.today().isoformat()
        rows = connection.execute('''SELECT * FROM law_articles WHERE effective_from <= ?
            AND (effective_to IS NULL OR effective_to > ?)''', (today, today)).fetchall()
        return [dict(row) for row in rows if _valid_url(row['source'], LAW_HOSTS)]
    finally:
        connection.close()


def _tokens(text: str) -> list[str]:
    """Chinese characters/bigrams plus Latin words, no large tokenizer dependency."""
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    for span in re.findall(r'[\u3400-\u9fff]+', text):
        tokens.extend(span)
        tokens.extend(span[index:index + 2] for index in range(len(span) - 1))
    return tokens


def _bm25(query: str, rows: list[dict]) -> list[tuple[str, float]]:
    documents = [Counter(_tokens(row['law_name'] + row['content'])) for row in rows]
    lengths = [sum(item.values()) for item in documents]
    avg_length = sum(lengths) / max(len(lengths), 1) or 1
    scores = []
    for row, counts, length in zip(rows, documents, lengths):
        score = 0.0
        for token in set(_tokens(query)):
            frequency = counts[token]
            if not frequency:
                continue
            doc_frequency = sum(token in document for document in documents)
            inverse = math.log(1 + (len(rows) - doc_frequency + 0.5) / (doc_frequency + 0.5))
            score += inverse * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * length / avg_length))
        if score > 0:
            scores.append((row['id'], score))
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def _vectors(query: str, rows: list[dict]) -> list[tuple[str, float]]:
    from langchain_openai import OpenAIEmbeddings
    model_name = os.getenv('EMBEDDING_MODEL', '').strip()
    endpoint = os.getenv('EMBEDDING_BASE_URL', '').strip()
    embedder = OpenAIEmbeddings(api_key=os.environ['EMBEDDING_API_KEY'], model=model_name,
                                base_url=endpoint or None, request_timeout=10, max_retries=0,
                                check_embedding_ctx_length=False)
    connection = _connect()
    try:
        vectors = {}
        missing = []
        for row in rows:
            cached = connection.execute('''SELECT vector FROM law_embeddings
                WHERE article_id=? AND model=? AND endpoint=? AND content=?''',
                (row['id'], model_name, endpoint, row['content'])).fetchone()
            if cached:
                vectors[row['id']] = json.loads(cached['vector'])
            else:
                missing.append(row)
        if missing:
            embedded = embedder.embed_documents([row['content'] for row in missing])
            for row, vector in zip(missing, embedded):
                vectors[row['id']] = vector
                connection.execute('INSERT OR REPLACE INTO law_embeddings VALUES (?, ?, ?, ?, ?)',
                                   (row['id'], model_name, endpoint, row['content'], json.dumps(vector)))
            connection.commit()
        query_vector = embedder.embed_query(query)
        query_norm = math.sqrt(sum(value * value for value in query_vector)) or 1
        ranked = []
        for identifier, vector in vectors.items():
            if len(vector) != len(query_vector):
                raise ValueError('向量维度不一致')
            denominator = math.sqrt(sum(value * value for value in vector)) * query_norm or 1
            similarity = sum(a * b for a, b in zip(vector, query_vector)) / denominator
            if similarity > 0:
                ranked.append((identifier, similarity))
        return sorted(ranked, key=lambda item: (-item[1], item[0]))
    finally:
        connection.close()


def search_local_law(query: str, limit: int = 5) -> dict:
    try:
        rows = _active_laws()
        if not rows:
            return {'laws': [], 'status': 'empty', 'mode': 'bm25'}
        lexical = _bm25(query, rows)
        rankings = [lexical]
        mode = 'bm25'
        if os.getenv('EMBEDDING_API_KEY', '').strip() and os.getenv('EMBEDDING_MODEL', '').strip():
            try:
                rankings.append(_vectors(query, rows))
                mode = 'hybrid'
            except Exception:
                mode = 'bm25_embedding_unavailable'
        fused = Counter()
        for ranking in rankings:
            for rank, (identifier, _) in enumerate(ranking[:20], 1):
                fused[identifier] += 1 / (60 + rank)
        lookup = {row['id']: row for row in rows}
        laws = [lookup[identifier] for identifier, _ in fused.most_common(limit)]
        return {'laws': laws, 'status': 'ok' if laws else 'no_results', 'mode': mode}
    except (sqlite3.Error, OSError, ValueError):
        return {'laws': [], 'status': 'unavailable', 'mode': 'bm25'}


def search_web_experience(query: str) -> dict:
    key = os.getenv('BOCHA_API_KEY', '').strip()
    if not key:
        return {'cases': [], 'status': 'not_configured'}
    topic_terms = ('预付式消费', '商品质量', '退货退款', '格式条款', '虚假宣传', '自动续费', '个人信息', '网络购物', '服务合同')
    safe_query = ' '.join(term for term in topic_terms if term in query) or '消费纠纷 协商 案例'
    try:
        response = httpx.post(
            os.getenv('BOCHA_BASE_URL', 'https://api.bochaai.com/v1/web-search'),
            json={'query': safe_query, 'summary': True, 'count': 8,
                  'include': '|'.join(sorted(ALLOWED_CASE_HOSTS))},
            headers={'Authorization': f'Bearer {key}'}, timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return {'cases': [], 'status': 'invalid_response'}
        # Some gateways report a business error in a successful HTTP response.
        code = payload.get('code')
        if code is not None and str(code) != '200':
            return {'cases': [], 'status': _bocha_error_status(code)}
        data = payload.get('data')
        if not isinstance(data, dict):
            return {'cases': [], 'status': 'invalid_response'}
        pages = data.get('webPages')
        if pages is None:
            results = []
        elif isinstance(pages, dict) and isinstance(pages.get('value'), list):
            results = pages['value']
        else:
            return {'cases': [], 'status': 'invalid_response'}
        allowed = []
        seen = set()
        for item in results:
            if not isinstance(item, dict):
                continue
            url = item.get('url', '')
            if isinstance(url, str) and _valid_url(url, ALLOWED_CASE_HOSTS) and url not in seen:
                seen.add(url)
                allowed.append({'title': str(item.get('name', ''))[:200], 'url': url,
                                'summary': str(item.get('summary') or item.get('snippet', ''))[:2000],
                                'kind': 'court_case' if urlparse(url).hostname == 'anli.court.gov.cn' else 'consumer_report'})
        return {'cases': allowed[:5], 'status': 'ok' if allowed else 'no_results',
                'result_count': len(results), 'allowed_count': len(allowed)}
    except httpx.HTTPStatusError as exc:
        return {'cases': [], 'status': _bocha_error_status(exc.response.status_code)}
    except httpx.TimeoutException:
        return {'cases': [], 'status': 'timeout'}
    except (ValueError, TypeError, AttributeError):
        return {'cases': [], 'status': 'invalid_response'}
    except httpx.HTTPError:
        return {'cases': [], 'status': 'unavailable'}


def _bocha_error_status(code) -> str:
    # Never return provider exception text, request headers or response bodies:
    # they can contain credentials and are unnecessary for setup diagnostics.
    return {'400': 'invalid_request', '401': 'unauthorized', '402': 'payment_required',
            '403': 'forbidden', '429': 'rate_limited'}.get(str(code), 'provider_error')


def search(query: str, tools: list[str] | None = None) -> dict:
    tools = tools if tools is not None else ['search_local_law', 'search_web_experience']
    local = search_local_law(query) if 'search_local_law' in tools else {'laws': [], 'status': 'not_requested', 'mode': 'none'}
    web = search_web_experience(query) if 'search_web_experience' in tools else {'cases': [], 'status': 'not_requested'}
    return {'laws': local['laws'], 'cases': web['cases'],
            'status': {'law_library': local['status'], 'law_search_mode': local['mode'], 'case_search': web['status']}}


def check_merchant_claims(text: str) -> list[dict]:
    """Look up an opponent's article claims separately from the model's sources.

    A missing match only describes this maintained local corpus, not all law.
    These are attributed input claims; they must never become allowed citations.
    """
    references = re.findall(
        r'《([^》\n]{1,80})》\s*第([一二三四五六七八九十百千万零〇\d]+)条', text)
    if not references:
        return []
    try:
        laws = _active_laws()
        available = True
    except (sqlite3.Error, OSError):
        laws, available = [], False
    checks = []
    seen = set()
    for name, number in references:
        article = normalize_article(number)
        identity = (_law_key(name), article)
        if identity in seen:
            continue
        seen.add(identity)
        same_law = [row for row in laws if _law_key(row['law_name']) == identity[0]]
        exact = next((row for row in same_law if row['article'] == article), None)
        status = ('matched' if exact else 'article_not_found' if same_law else
                  'law_not_in_library' if available else 'library_unavailable')
        checks.append({'claim': f'《{name}》第{number}条', 'law_name': name, 'article': article,
                       'status': status, 'law_id': exact['id'] if exact else None,
                       'scope': 'local_library_only'})
    return checks


def format_merchant_checks(checks: list[dict]) -> str:
    """Render attributed checks from code, outside the model's citation claims."""
    lines = []
    for check in checks:
        label = f'商家所称「{check["claim"]}」'
        if check['status'] == 'matched':
            lines.append(label + '：在本地库中找到对应条文；条文存在不代表支持商家的解释，适用条件仍需核对。')
        elif check['status'] == 'article_not_found':
            lines.append(label + '：未在本地已收录的该法律版本中找到，不能作为本轮已核验依据。')
        elif check['status'] == 'law_not_in_library':
            lines.append(label + '：本地尚无对应法律，不能据此断言法条不存在。')
        else:
            lines.append(label + '：本地库暂不可用，尚无法核对。')
    return '【商家法条主张核对（本地库）】\n' + '\n'.join(lines) if lines else ''


def audit_citations(text: str, laws: list[dict], citations: list[dict] | None = None) -> dict:
    """Check identity, current corpus membership and exact quotations.

    This validates source references, not legal applicability or every paraphrase.
    Only articles returned for this request can be cited. Bare article references
    are rejected since their law identity cannot be checked.
    """
    errors = []
    used = []
    try:
        active = {row['id']: row for row in _active_laws()} if laws else {}
    except (sqlite3.Error, OSError):
        active = {}
    allowed = {row['id']: row for row in laws if active.get(row['id']) == row}
    verified_quotes = []
    # A model can only cite an ID plus an exact quote from a retrieved article.
    for citation in citations or []:
        row = allowed.get(citation.get('law_id')) if isinstance(citation, dict) else None
        quote = citation.get('quote', '') if isinstance(citation, dict) else ''
        if not row or not isinstance(quote, str) or not quote.strip() or quote not in row['content']:
            errors.append('结构化引用不在当前法律库中，或引文与原文不符')
        else:
            used.append(row['id'])
            verified_quotes.append(quote)
    # Exact quotes often contain their own bare article number or references to
    # other provisions. Once checked verbatim, do not treat those as new model
    # assertions; all surrounding model prose is still audited normally.
    for quote in sorted(verified_quotes, key=len, reverse=True):
        text = text.replace(quote, '[已逐字核验的原文]')
    # Names inside book-title brackets cover 民法典/条例/规定, not just names ending in 法.
    named_pattern = r'《([^》\n]{1,80})》\s*第([一二三四五六七八九十百千万零〇\d]+)条'
    matches = list(re.finditer(named_pattern, text))
    for match in matches:
        name, article = match.groups()
        number = normalize_article(article)
        candidates = [row for row in allowed.values() if _law_key(row['law_name']) == _law_key(name) and row['article'] == number]
        if not candidates:
            errors.append(f'《{name}》第{article}条不在本次已核验检索结果中')
        else:
            used.append(candidates[0]['id'])
    rest = re.sub(named_pattern, '', text)
    if re.search(r'第[一二三四五六七八九十百千万零〇\d]+条', rest):
        errors.append('存在未标明完整法律名称的条号，请删除或改成完整可核验引用')
    if re.search(r'《[^》]+》', rest):
        errors.append('存在缺少条号的法律引用，请仅使用结构化法条来源')
    allowed_urls = {row['source'] for row in allowed.values()}
    for url in re.findall(r'https?://[^\s<>"）)]+', text):
        if url.rstrip('。，；') not in allowed_urls:
            errors.append('回复包含未经核验的链接，请改用系统提供的来源')
    for quote in re.findall(r'[“「]([^”」]{8,})[”」]', text):
        if re.search(r'法律原文|法条原文|法律规定如下', text) and not any(quote in row['content'] for row in allowed.values()):
            errors.append('声称为法律原文的引文无法在检索结果中找到')
    return {'valid': not errors, 'invalid_citations': errors, 'used_law_ids': sorted(set(used)),
            'feedback': '' if not errors else '引用校验失败：' + '；'.join(errors) + '。仅依据检索原文重写；没有原文则删除法律引用。不要在正文复述商家错误条号，即使为了反驳，也统一写“商家所引条号”，具体核对结果由系统另行展示。',
            'scope': 'source_identity_and_quote_only'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='导入人工复核的官方法条 JSONL')
    parser.add_argument('corpus')
    args = parser.parse_args()
    print(f'Imported {import_laws(args.corpus)} articles')
