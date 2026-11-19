"""只读查看当前 DATABASE_URL（默认 MySQL），不修改任何记录。

用法（在 backend 目录执行）：
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py                 列出所有表与行数
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py cases           列出 cases 每条记录的概要
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py cases --full    输出完整 payload
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py --id <案件ID>    查看单个案件完整内容
    .\\.venv\\Scripts\\python.exe tools\\dump_db.py --db <文件路径>  指定其他数据库文件
"""

import argparse
from contextlib import closing
import json
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


class SqlReader:
    """Keep the existing SQLite-only --db mode while supporting the active DB."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, parameters=None):
        return self.connection.execute(text(statement), parameters or {})


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
    names = inspect(conn.connection).get_table_names() if isinstance(conn, SqlReader) else [
        row[0] for row in conn.execute("select name from sqlite_master where type='table' order by name")]
    print(f'共 {len(names)} 张表')
    for name in names:
        quoted = conn.connection.dialect.identifier_preparer.quote(name) if isinstance(conn, SqlReader) else '"' + name.replace('"', '""') + '"'
        count = conn.execute(f'select count(*) from {quoted}').fetchone()[0]
        print(f'  - {name}: {count} 行')


def show_cases(conn: sqlite3.Connection, limit=None, full=False):
    if isinstance(conn, SqlReader):
        from sqlalchemy.orm import Session
        from sqlalchemy import select
        from app.database import CaseRecord
        from app.services.case_repository import load_case
        with Session(bind=conn.connection) as session:
            rows = [(record.id, load_case(record)) for record in session.scalars(select(CaseRecord).order_by(CaseRecord.id))]
    else:
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
    if isinstance(conn, SqlReader):
        from sqlalchemy.orm import Session
        from app.database import CaseRecord
        from app.services.case_repository import load_case
        with Session(bind=conn.connection) as session:
            record = session.get(CaseRecord, case_id)
            if record is None:
                raise SystemExit('未找到案件。')
            print(json.dumps(load_case(record), ensure_ascii=False, indent=2))
        return
    row = conn.execute('select payload from cases where id = :id', {'id': case_id}).fetchone()
    if not row:
        raise SystemExit(f'未找到案件：{case_id}')
    print(json.dumps(parse_payload(row[0]), ensure_ascii=False, indent=2))


def show_table(conn: sqlite3.Connection, table: str):
    if isinstance(conn, SqlReader):
        if table not in inspect(conn.connection).get_table_names():
            raise SystemExit('表不存在。')
        quoted = conn.connection.dialect.identifier_preparer.quote(table)
        result = conn.execute(f'select * from {quoted}')
        columns, rows = list(result.keys()), result.fetchall()
        print(' | '.join(columns))
        for row in rows:
            print(' | '.join(str(parse_payload(value)) for value in row))
        return
    try:
        rows = conn.execute(f'select * from "{table}"').fetchall()
        columns = [item[0] for item in conn.execute(f'select * from "{table}"').description]
    except sqlite3.Error as error:
        raise SystemExit(f'读取表 {table} 失败：{error}')
    print(' | '.join(columns))
    for row in rows:
        print(' | '.join(str(parse_payload(value)) for value in row))


def main():
    parser = argparse.ArgumentParser(description='只读查看当前业务数据库，支持 MySQL / SQLite')
    parser.add_argument('table', nargs='?', help='要查看的表名，默认列出所有表')
    parser.add_argument('--full', action='store_true', help='输出完整 JSON')
    parser.add_argument('--id', dest='case_id', help='按案件 ID 查看完整内容')
    parser.add_argument('--db', help='显式查看 SQLite 备份文件；默认使用 backend/.env 中的 DATABASE_URL')
    args = parser.parse_args()

    def show(conn):
        if args.case_id:
            show_case(conn, args.case_id)
        elif not args.table:
            list_tables(conn)
        elif args.table == 'cases':
            show_cases(conn, full=args.full)
        else:
            show_table(conn, args.table)

    if args.db:
        db_path = Path(args.db)
        with closing(open_db(db_path)) as conn:
            print(f'SQLite 备份：{db_path}')
            show(conn)
    else:
        from app.database import DATABASE_URL
        engine = create_engine(DATABASE_URL)
        try:
            with engine.connect() as connection:
                if engine.dialect.name == 'mysql':
                    connection.execute(text('SET TRANSACTION READ ONLY'))
                elif engine.dialect.name == 'sqlite':
                    connection.execute(text('PRAGMA query_only=ON'))
                print(f'数据库：{engine.dialect.name} / {engine.url.database}')
                show(SqlReader(connection))
        finally:
            engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # SQL driver exceptions can contain connection/SQL parameters.
        raise SystemExit(f'读取失败（{type(error).__name__}），请检查数据库已启动及本地连接配置。')
