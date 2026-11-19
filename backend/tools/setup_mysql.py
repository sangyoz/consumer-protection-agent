"""Prepare project-local MySQL, preserve existing cases, and save only the DB setting.

Run from the project root: backend/.venv/Scripts/python.exe backend/tools/setup_mysql.py
An existing reachable MySQL DATABASE_URL is used as-is. Otherwise a dedicated
Windows runtime is downloaded from Oracle; no admin/service/Docker is required.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile

from dotenv import dotenv_values, set_key
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
RUN = ROOT / '.run' / 'mysql'
VERSION = '8.4.13'
DOWNLOAD = f'https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-{VERSION}-winx64.zip'
COMPOSE_URL = 'mysql+pymysql://youli:youli_dev_password@127.0.0.1:3306/youli?charset=utf8mb4'
sys.path.insert(0, str(BACKEND))


def connectable(url):
    engine = create_engine(url, connect_args={'connect_timeout': 3}, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


def prepare_local():
    if os.name != 'nt':
        raise RuntimeError('自动安装仅支持 Windows；其他系统请使用 compose.yaml 并配置 DATABASE_URL。')
    RUN.mkdir(parents=True, exist_ok=True)
    credentials_path = RUN / 'credentials.json'
    if credentials_path.exists():
        credentials = json.loads(credentials_path.read_text(encoding='utf-8'))
    else:
        credentials = {'user': 'youli', 'password': secrets.token_hex(24), 'root_password': secrets.token_hex(32)}
        credentials_path.write_text(json.dumps(credentials), encoding='utf-8')
    url = URL.create('mysql+pymysql', username=credentials['user'], password=credentials['password'],
                     host='127.0.0.1', port=3306, database='youli', query={'charset': 'utf8mb4'})
    if connectable(url):
        return url
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', 3306)) == 0:
            raise RuntimeError('3306 已被其他数据库占用。请在 backend/.env 配置该数据库的 DATABASE_URL 后重试。')
    runtime = RUN / f'mysql-{VERSION}-winx64'
    executable = runtime / 'bin' / 'mysqld.exe'
    if not executable.exists():
        archive = RUN / f'mysql-{VERSION}-winx64.zip'
        if not archive.exists() or not zipfile.is_zipfile(archive):
            print(f'首次启动：从 MySQL 官方下载 {VERSION}（约 268 MB）…', flush=True)
            urllib.request.urlretrieve(DOWNLOAD, archive)
        print('解压 MySQL…', flush=True)
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                if not (RUN / member.filename).resolve().is_relative_to(RUN.resolve()):
                    raise RuntimeError('MySQL 安装包包含非法路径。')
            package.extractall(RUN)
    data = RUN / 'data'
    config = RUN / 'my.ini'
    shared_config = RUN / 'sharing.json'
    bind_address = json.loads(shared_config.read_text(encoding='utf-8')).get('bind_address', '127.0.0.1') if shared_config.exists() else '127.0.0.1'
    config.write_text('\n'.join([
        '[mysqld]', f'basedir="{runtime.as_posix()}"', f'datadir="{data.as_posix()}"',
        f'bind-address={bind_address}', 'port=3306', 'mysqlx=OFF',
        'character-set-server=utf8mb4', 'collation-server=utf8mb4_0900_ai_ci',
        'innodb-buffer-pool-size=128M', f'log-error="{(RUN / "mysql.err.log").as_posix()}"',
        f'pid-file="{(RUN / "mysql.pid").as_posix()}"',
    # Windows MySQL reads option-file paths in the system code page (including
    # Chinese workspace paths); UTF-8 here can make an existing directory fail.
    ]) + '\n', encoding='mbcs')
    bootstrap = RUN / 'bootstrap.sql'
    if not (data / 'mysql').exists():
        print('初始化本地 MySQL…', flush=True)
        # Passwords are random hexadecimal; SQL never contains user-supplied strings.
        bootstrap.write_text('\n'.join([
            f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{credentials['root_password']}';",
            'CREATE DATABASE IF NOT EXISTS youli CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;',
            f"CREATE USER IF NOT EXISTS 'youli'@'localhost' IDENTIFIED BY '{credentials['password']}';",
            "GRANT ALL PRIVILEGES ON youli.* TO 'youli'@'localhost';",
        ]) + '\n', encoding='utf-8')
        result = subprocess.run([f'mysql-{VERSION}-winx64/bin/mysqld.exe', '--defaults-file=my.ini', '--initialize-insecure'],
                                executable=str(executable), cwd=RUN,
                                creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
        if result.returncode:
            raise RuntimeError('MySQL 初始化失败，请查看 .run/mysql/mysql.err.log。')
    # ASCII argv and a Unicode-aware working directory avoid MySQL's Windows
    # command-line parser truncating an executable path containing Chinese.
    arguments = [f'mysql-{VERSION}-winx64/bin/mysqld.exe', '--defaults-file=my.ini']
    if bootstrap.exists():
        with config.open('a', encoding='mbcs') as options:
            options.write(f'init-file="{bootstrap.as_posix()}"\n')
    process = subprocess.Popen(arguments, executable=str(executable), cwd=RUN, creationflags=subprocess.CREATE_NO_WINDOW,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError('MySQL 启动失败，请查看 .run/mysql/mysql.err.log。')
        if connectable(url):
            bootstrap.unlink(missing_ok=True)
            return url
        time.sleep(1)
    raise RuntimeError('MySQL 未按时就绪，请查看 .run/mysql/mysql.err.log。')


def main():
    env_file = BACKEND / '.env'
    configured = os.environ.get('DATABASE_URL') or dotenv_values(env_file).get('DATABASE_URL') or ''
    if configured.startswith('mysql'):
        url = make_url(configured)
        if not connectable(url):
            owned_path = RUN / 'credentials.json'
            owned = json.loads(owned_path.read_text()) if owned_path.exists() else {}
            is_local = (url.host in ('localhost', '127.0.0.1') and (url.port or 3306) == 3306
                        and url.username == owned.get('user') and url.password == owned.get('password')
                        and url.database == 'youli')
            if configured != COMPOSE_URL and not is_local:
                raise RuntimeError('配置的 MySQL 无法连接，请检查 DATABASE_URL、账号及数据库是否已启动。')
            url = prepare_local()
    else:
        url = prepare_local()
    from app.services.database_migration import migrate_cases
    settings = dotenv_values(env_file)
    skip_import = (os.environ.get('SKIP_SQLITE_IMPORT') or settings.get('SKIP_SQLITE_IMPORT')) == '1'
    engine = create_engine(url, pool_pre_ping=True)
    try:
        RUN.mkdir(parents=True, exist_ok=True)
        marker = RUN / 'migration.json'
        # Track each destination separately; never replay stale SQLite after MySQL edits.
        identity = str(url._replace(password=None))
        previous = json.loads(marker.read_text(encoding='utf-8')) if marker.exists() else {}
        if skip_import:
            from app.services.schema_migration import upgrade_schema
            upgrade_schema(engine)
            print('共享数据库模式：跳过本机 SQLite 导入。', flush=True)
        elif previous.get('destination') != identity:
            backup = ROOT / '.run' / 'backups' / f'youli-before-mysql-{time.time_ns()}.db'
            result = migrate_cases(BACKEND / 'youli.db', engine, backup)
            marker.write_text(json.dumps({'destination': identity, **result}), encoding='utf-8')
            print(f"案件迁移完成：新增 {result['inserted']}，已存在 {result['existing']}；SQLite 原库保留。", flush=True)
        else:
            print('使用已有 MySQL 数据，跳过重复迁移。', flush=True)
        set_key(str(env_file), 'DATABASE_URL', url.render_as_string(hide_password=False))
        with engine.connect() as connection:
            count = connection.execute(text('SELECT COUNT(*) FROM cases')).scalar_one()
        print(f'MySQL 连接正常：{url.host}:{url.port or 3306}/{url.database}，{count} 个案件。', flush=True)
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Never print SQLAlchemy URLs, SQL parameters, or account passwords.
        message = str(error) if isinstance(error, (RuntimeError, ValueError)) else type(error).__name__
        print(f'MySQL 配置失败：{message}', file=sys.stderr)
        sys.exit(1)
