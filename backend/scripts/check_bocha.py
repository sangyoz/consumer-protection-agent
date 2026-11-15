"""Run one Bocha search without calling the chat model or changing case data."""
import argparse
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.retrieval import search_web_experience


MESSAGES = {
    'not_configured': '未配置：请在 backend/.env 填写 BOCHA_API_KEY。',
    'ok': '连接成功，已取得白名单案例。',
    'no_results': '请求成功，但本轮没有可用的白名单案例；不代表密钥失效。',
    'unauthorized': '认证失败：请检查博查 API Key 是否正确、有效。',
    'payment_required': '服务要求付费：请到博查控制台检查账户余额和服务开通情况。',
    'forbidden': '访问被拒绝：请在博查控制台检查 API 权限及账户状态。',
    'rate_limited': '请求受限：请稍后再试，并检查账户调用限额。',
    'invalid_request': '请求参数被拒绝：请核对所用 API 地址和接口文档。',
    'timeout': '搜索超时：请检查网络或稍后重试。',
    'invalid_response': '响应格式异常：请确认连接的是博查 Web Search API。',
    'provider_error': '博查返回服务错误：请到控制台检查服务状态。',
    'unavailable': '连接失败：请检查网络和 BOCHA_BASE_URL。',
}


def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', default='退货退款 商品质量',
                        help='使用通用纠纷主题；工具仅向博查发送匹配的主题词。')
    args = parser.parse_args()
    load_dotenv(BACKEND_DIR / '.env')
    print('BOCHA_API_KEY: ' + ('已填写（不显示密钥）' if os.getenv('BOCHA_API_KEY', '').strip() else '未填写'))
    result = search_web_experience(args.query)
    status = result['status']
    print('状态: ' + status)
    print(MESSAGES.get(status, '未知状态。'))
    if 'result_count' in result:
        print(f'接口结果数: {result["result_count"]}；白名单通过数: {result["allowed_count"]}')
    for case in result['cases']:
        print(f'- {case["title"]}\n  {case["url"]}\n  类型: {case["kind"]}')
    return 0 if status in {'ok', 'no_results'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
