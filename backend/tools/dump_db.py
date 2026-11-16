"""只读查看本地 SQLite 数据，不修改任何记录。

用法（在 backend 目录执行）：
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py                 列出所有表与行数
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py cases           列出 cases 每条记录的概要
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py cases --full    输出完整 payload
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py --id <案件ID>    查看单个案件完整内容
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py --db <文件路径>  指定其他数据库文件
"""

import argparse
import json
import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def open_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise SystemExit(f'数据库文件不存在：{path}')
    # 只读方式打开，避免误写。
    return sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True)


def parse_payload(value):
    if isinstance(value, (str, bytes)):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def list_tables(conn: sqlite3.Connection):
    rows = conn.execute("select name from sqlite_master where type='table' order by name").fetchall()
    print(f'共 {len(rows)} 张表')
    for (name,) in rows:
        count = conn.execute(f'select count(*) from "{name}"').fetchone()[0]
        print(f'  - {name}: {count} 行')


def show_cases(conn: sqlite3.Connection, limit=None, full=False):
    rows = conn.execute('select id, payload from cases order by id').fetchall()
    if limit:
        rows = rows[:limit]
    for index, (case_id, payload) in enumerate(rows, 1):
        case = parse_payload(payload)
        if full:
            print(f'--- [{index}] {case_id} ---')
            print(json.dumps(case, ensure_ascii=False, indent=2))
            continue
        materials = case.get('materials') or []
        followups = case.get('followups') or []
        plan = case.get('goalPlan') or {}
        resolution = case.get('resolution')
        print(f'[{index}] {case_id}')
        print(f'    标题     {case.get("title", "")}')
        print(f'    阶段     {case.get("stage", "")}')
        print(f'    商家/金额 {case.get("merchant") or "待补充"} / {case.get("amount")}')
        print(f'    材料     {len(materials)} 份；跟进 {len(followups)} 条；消息 {len(case.get("messages") or [])} 条')
        print(f'    诉求确认 {bool(plan.get("confirmed"))}；结案 {bool(resolution)}')
        print(f'    更新时间 {case.get("updatedAt", "")}')
    if not rows:
        print('尚无用例记录。API 模式下新建案件后才会写入。')


def show_case(conn: sqlite3.Connection, case_id: str):
    row = conn.execute('select payload from cases where id = ?', (case_id,)).fetchone()
    if not row:
        raise SystemExit(f'未找到案件：{case_id}')
    print(json.dumps(parse_payload(row[0]), ensure_ascii=False, indent=2))


def show_table(conn: sqlite3.Connection, table: str):
    try:
        rows = conn.execute(f'select * from "{table}"').fetchall()
        columns = [item[0] for item in conn.execute(f'select * from "{table}"').description]
    except sqlite3.Error as error:
        raise SystemExit(f'读取表 {table} 失败：{error}')
    print(' | '.join(columns))
    for row in rows:
        print(' | '.join(str(parse_payload(value)) for value in row))


def main():
    parser = argparse.ArgumentParser(description='只读查看有理项目 SQLite 数据')
    parser.add_argument('table', nargs='?', help='要查看的表名，默认列出所有表')
    parser.add_argument('--full', action='store_true', help='输出完整 JSON')
    parser.add_argument('--id', dest='case_id', help='按案件 ID 查看完整内容')
    parser.add_argument('--db', default=str(BACKEND_DIR / 'youli.db'), help='数据库文件路径')
    args = parser.parse_args()

    db_path = Path(args.db)
    with open_db(db_path) as conn:
        print(f'数据库：{db_path}')
        if args.case_id:
            show_case(conn, args.case_id)
        elif not args.table:
            list_tables(conn)
        elif args.table == 'cases':
            show_cases(conn, full=args.full)
        else:
            show_table(conn, args.table)


if __name__ == '__main__':
    main()
