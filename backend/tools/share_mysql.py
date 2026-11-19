"""Share this project's local MySQL with a specified LAN; never prints passwords.

Run after stopping application writers:
  python backend/tools/share_mysql.py --host <this-PC-IP> --network <LAN-CIDR>
The generated private .run/shared-database.env is handed to the teammate, not Git.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import secrets
import sys
import time

from dotenv import set_key
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '.run' / 'mysql'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_mysql import prepare_local


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--network', required=True)
    args = parser.parse_args()
    host = ipaddress.IPv4Address(args.host)
    network = ipaddress.IPv4Network(args.network, strict=False)
    if host not in network or not host.is_private:
        raise ValueError('请使用本机局域网 IPv4 与对应网段。')
    credentials = json.loads((RUN / 'credentials.json').read_text(encoding='utf-8'))
    share_path = RUN / 'sharing.json'
    old = json.loads(share_path.read_text(encoding='utf-8')) if share_path.exists() else {}
    password = old.get('password') or secrets.token_hex(24)
    account_host = f'{network.network_address}/{network.netmask}'
    admin_url = URL.create('mysql+pymysql', username='root', password=credentials['root_password'], host='127.0.0.1', port=3306)
    admin = create_engine(admin_url)
    with admin.begin() as connection:
        connection.execute(text('CREATE USER IF NOT EXISTS :user@:host IDENTIFIED BY :password'),
                           {'user': 'youli_shared', 'host': account_host, 'password': password})
        connection.execute(text('ALTER USER :user@:host IDENTIFIED BY :password'),
                           {'user': 'youli_shared', 'host': account_host, 'password': password})
        connection.execute(text('GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON youli.* TO :user@:host'),
                           {'user': 'youli_shared', 'host': account_host})
    share_path.write_text(json.dumps({'bind_address': f'127.0.0.1,{host}', 'host': str(host),
                                      'network': str(network), 'account_host': account_host,
                                      'password': password}), encoding='utf-8')
    try:
        with admin.connect() as connection:
            connection.execute(text('SHUTDOWN'))
    except OperationalError as error:
        if error.orig.args[0] not in (2006, 2013):
            raise
    admin.dispose()
    time.sleep(3)
    prepare_local()
    url = URL.create('mysql+pymysql', username='youli_shared', password=password, host=str(host),
                     port=3306, database='youli', query={'charset': 'utf8mb4'})
    target = ROOT / '.run' / 'shared-database.env'
    target.touch(exist_ok=True)
    set_key(str(target), 'DATABASE_URL', url.render_as_string(hide_password=False))
    # A teammate must connect to this existing schema, never import their stale local DB.
    set_key(str(target), 'SKIP_SQLITE_IMPORT', '1')
    with create_engine(url).connect() as connection:
        count = connection.execute(text('SELECT COUNT(*) FROM cases')).scalar_one()
    print(f'局域网数据库已监听 {host}:3306；网段 {network}；现有案件 {count} 个。')
    print('私密连接配置：.run/shared-database.env（请私下发给同学，不要上传 GitHub）。')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        original = getattr(error, 'orig', None)
        number = original.args[0] if original and original.args else ''
        print(f'共享配置失败：{type(error).__name__} {number}。请检查本机数据库与网段配置。', file=sys.stderr)
        sys.exit(1)
