"""Convert downloaded Chinese law TXT files to article-level UTF-8 JSONL.

Only the Python standard library is needed. Running without arguments reads
backend/data/laws/raw and writes a draft, a metadata template and a report.
Ready-to-import output is published only when every file's metadata is complete.
The script never edits the raw text, application .env or live law database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_DIRECTORY = BACKEND / 'data' / 'laws'
OFFICIAL_HOSTS = {'flk.npc.gov.cn', 'www.npc.gov.cn', 'npc.gov.cn', 'www.gov.cn'}
NUMERALS = r'[零〇一二三四五六七八九十百千万两0-9]+'
# Anchor at line start: references to other articles within a paragraph must not
# become new records. 规定 is removed only for the downloaded reporting format.
ARTICLE = re.compile(
    rf'(?m)^[ \t\u3000]*(?:《(?P<law>[^》\n]+)》[ \t\u3000]*)?'
    rf'第(?P<number>{NUMERALS})条'
    rf'(?P<suffix>之{NUMERALS})?'
    rf'(?=[ \t\u3000：:，,\n]|规定|[【\[])'
    rf'[ \t\u3000]*(?:规定[ \t\u3000]*[，,：:]?[ \t\u3000]*)?'
)
SECTION = re.compile(r'^[ \t\u3000]*第' + NUMERALS + r'[编章节][^\n]*$')


def article_number(value: str) -> str:
    if value.isdigit():
        return str(int(value))
    digits = dict(zip('零〇一二三四五六七八九两', (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2)))
    units = {'十': 10, '百': 100, '千': 1000, '万': 10000}
    total = section = number = 0
    for char in value:
        if char in digits:
            number = digits[char]
        elif char == '万':
            total += (section + number) * 10000
            section = number = 0
        elif char in units:
            section += (number or 1) * units[char]
            number = 0
        else:
            raise ValueError(f'不支持的条号：{value}')
    return str(total + section + number)


def read_text(path: Path, encoding: str | None = None) -> tuple[str, str]:
    raw = path.read_bytes()
    candidates = [encoding] if encoding else ['utf-8-sig']
    if not encoding and raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        candidates = ['utf-16']
    elif not encoding:
        candidates.append('gb18030')
    for candidate in candidates:
        try:
            text = raw.decode(candidate)
        except UnicodeError:
            continue
        if '\x00' in text or '\ufffd' in text:
            continue
        return text.replace('\r\n', '\n').replace('\r', '\n'), candidate
    raise ValueError(f'{path.name} 无法按候选编码读取，请用 --encoding 指定编码')


def split_articles(text: str, law_name: str, file_name: str) -> tuple[list[dict], list[str]]:
    matches = list(ARTICLE.finditer(text))
    if not matches:
        raise ValueError(f'{file_name} 未识别到行首的“第X条”')
    rows = []
    seen = set()
    removed_headers = []
    for index, match in enumerate(matches):
        if match['law'] and match['law'] != law_name:
            raise ValueError(f'{file_name}：标题“{match["law"]}”与元数据法律名“{law_name}”不一致')
        if match['suffix']:
            # The existing law importer does not support 条之一. Do not silently
            # merge it into the preceding article or discard the suffix.
            raise ValueError(f'{file_name} 含第{match["number"]}条{match["suffix"]}，需先扩展法律库条号结构')
        number = article_number(match['number'])
        if number in seen:
            raise ValueError(f'{file_name} 条号 {number} 重复，可能混入目录或多个版本，请检查原文')
        seen.add(number)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body_lines = []
        for line in text[match.end():end].splitlines():
            if SECTION.fullmatch(line):
                removed_headers.append(line.strip())
            else:
                body_lines.append(line.rstrip())
        body = '\n'.join(body_lines).strip()
        if not body:
            raise ValueError(f'{file_name} 第{number}条正文为空')
        rows.append({
            'article': number,
            'content': f'第{match["number"]}条 {body}',
            'source_file': file_name,
            'source_line': text.count('\n', 0, match.start()) + 1,
        })
    warnings = []
    numbers = [int(row['article']) for row in rows]
    missing = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
    if missing:
        warnings.append('条号有缺口，请检查是否有意节选：' + ', '.join(map(str, missing[:50])))
    if numbers != sorted(numbers):
        warnings.append('原文条号不是升序，请检查文本顺序')
    if removed_headers:
        warnings.append(f'分离了 {len(removed_headers)} 行编/章/节标题，未并入法条正文')
    return rows, warnings


def metadata_errors(meta: dict) -> list[str]:
    errors = []
    for key in ('law_name', 'source', 'effective_from', 'reviewed_at'):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            errors.append(f'缺少 {key}')
    source = meta.get('source') or ''
    parsed = urlparse(source)
    if source and not (parsed.scheme == 'https' and parsed.hostname in OFFICIAL_HOSTS
                       and not parsed.username and not parsed.password):
        errors.append('source 必须是法律库允许的官方 HTTPS 链接')
    dates = {}
    for key in ('effective_from', 'reviewed_at', 'effective_to'):
        value = meta.get(key)
        if not value:
            continue
        try:
            dates[key] = date.fromisoformat(value)
        except (TypeError, ValueError):
            errors.append(f'{key} 必须为 YYYY-MM-DD')
    if dates.get('reviewed_at', date.min) > date.today():
        errors.append('reviewed_at 不能是未来日期')
    if dates.get('effective_to') and dates.get('effective_from') and dates['effective_to'] < dates['effective_from']:
        errors.append('effective_to 早于 effective_from')
    return errors


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')
    temporary.replace(path)


def convert(input_dir: Path, output: Path, ready_output: Path, metadata_path: Path,
            report_path: Path, encoding: str | None = None) -> dict:
    paths = sorted(input_dir.glob('*.txt'))
    if not paths:
        raise ValueError(f'没有找到 TXT 文件：{input_dir}')
    resolved_outputs = [p.resolve() for p in (output, ready_output, metadata_path, report_path)]
    if len(set(resolved_outputs)) != len(resolved_outputs) or any(p.resolve() in resolved_outputs for p in paths):
        raise ValueError('输入文件、草稿、正式输出、元数据和报告的路径必须互不相同')
    metadata = json.loads(metadata_path.read_text(encoding='utf-8-sig')) if metadata_path.exists() else {}
    if not isinstance(metadata, dict):
        raise ValueError('元数据应为以 TXT 文件名为键的 JSON 对象')
    all_rows = []
    report = {'total_articles': 0, 'files': [], 'ready': False, 'ready_output_updated': False}
    errors = []
    ids = set()
    for path in paths:
        meta = metadata.setdefault(path.name, {'law_name': path.stem, 'source': '', 'effective_from': '',
                                                'reviewed_at': '', 'effective_to': None})
        if not isinstance(meta, dict):
            raise ValueError(f'{path.name} 的元数据不是 JSON 对象')
        text, used_encoding = read_text(path, encoding)
        law_name = meta.get('law_name') or path.stem
        rows, warnings = split_articles(text, law_name, path.name)
        pending = metadata_errors(meta)
        errors.extend(pending)
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        for row in rows:
            identity = f'{law_name}|{row["article"]}|{meta.get("effective_from") or "unreviewed"}'
            identifier = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]
            if identifier in ids:
                raise ValueError('多份文件包含相同法律、版本和条号，请只保留一份原文')
            ids.add(identifier)
            row.update(id=identifier, law_name=law_name, source=meta.get('source', ''),
                       effective_from=meta.get('effective_from', ''), reviewed_at=meta.get('reviewed_at', ''),
                       effective_to=meta.get('effective_to') or None, raw_sha256=raw_hash)
        all_rows.extend(rows)
        report['files'].append({'file': path.name, 'encoding': used_encoding, 'articles': len(rows),
                                'first_article': rows[0]['article'], 'last_article': rows[-1]['article'],
                                'pending_metadata': pending, 'warnings': warnings, 'raw_sha256': raw_hash})
    report['total_articles'] = len(all_rows)
    report['ready'] = not errors
    write_json(metadata_path, metadata)  # Existing values, including user metadata, are preserved.
    write_jsonl(output, all_rows)
    if report['ready']:
        write_jsonl(ready_output, all_rows)
        report['ready_output_updated'] = True
    write_json(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='将法律 TXT 按条号转换为 JSONL；未补齐来源/版本日期时仅生成草稿')
    parser.add_argument('--input-dir', type=Path, default=DEFAULT_DIRECTORY / 'raw')
    parser.add_argument('--output', type=Path, default=DEFAULT_DIRECTORY / 'laws.draft.jsonl')
    parser.add_argument('--ready-output', type=Path, default=DEFAULT_DIRECTORY / 'laws.jsonl')
    parser.add_argument('--metadata', type=Path, default=DEFAULT_DIRECTORY / 'metadata.json')
    parser.add_argument('--report', type=Path, default=DEFAULT_DIRECTORY / 'conversion_report.json')
    parser.add_argument('--encoding', help='可选：手动指定 TXT 编码，如 utf-8 或 gb18030')
    args = parser.parse_args()
    try:
        result = convert(args.input_dir, args.output, args.ready_output, args.metadata, args.report, args.encoding)
    except (OSError, ValueError, LookupError) as exc:
        parser.exit(1, f'Conversion failed: {exc}\n')
    for entry in result['files']:
        print(f'{entry["file"]}: {entry["articles"]} articles')
    print(f'Total: {result["total_articles"]}; draft: {args.output}')
    if result['ready']:
        print(f'Ready for import: {args.ready_output}')
    else:
        print(f'Metadata incomplete. Edit: {args.metadata}')
        print('Ready output was NOT updated. No changes to the live database.')
    print(f'Report: {args.report}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
