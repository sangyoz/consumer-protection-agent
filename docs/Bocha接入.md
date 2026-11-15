# 博查 Web Search 接入

本项目已将博查接入 `search_web_experience` 工具。它检索案例经验，本地法律库负责法条依据，两者分别使用。无需安装额外 MCP 服务。

## 配置

1. 打开 [博查开放平台](https://open.bochaai.com/)，登录控制台，在 API KEY 管理中创建密钥，确认 Web Search 服务权限、额度或余额。费用以平台当时展示为准。
2. 编辑项目 `backend/.env`（不是 `.env.example`），填写以下配置。博查密钥独立于 DeepSeek 密钥，不要提交 Git 或发到聊天里。

```dotenv
BOCHA_API_KEY=这里替换成你的博查密钥
BOCHA_BASE_URL=https://api.bochaai.com/v1/web-search
```

项目保留上述官网首页示例地址；当前接口文档也使用 `https://api.bocha.cn/v1/web-search`，可通过 `BOCHA_BASE_URL` 配置完整接口地址。

3. 在项目根目录运行自检（会发出一次搜索请求，按平台规则计费；未填密钥不会请求）：

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\check_bocha.py
```

4. 修改 `.env` 后重新运行 `start.bat`，使后端加载新配置。

## 自检结果

| 状态 | 含义与处理 |
| --- | --- |
| `ok` | 接口成功，取得可用白名单案例 |
| `no_results` | 请求成功但无可用案例；可更换通用纠纷主题重试 |
| `not_configured` | 密钥未填入 `backend/.env` |
| `unauthorized` | 认证失败，检查密钥是否有效 |
| `payment_required` | 服务要求付费，检查账户服务和余额 |
| `forbidden` | 访问被拒绝，检查权限及账户状态 |
| `rate_limited` | 请求受限，检查限额并稍后重试 |
| `invalid_request` | 参数被拒绝，核对 API 地址和文档 |
| `timeout` / `unavailable` | 超时或连接失败，检查网络 |
| `invalid_response` / `provider_error` | 返回格式或服务错误，检查地址和平台状态 |

可选主题测试：

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\check_bocha.py --query "预付式消费 退货退款"
```

## 工作流行为

- Agent 按需选择检索工具；配置密钥不等于每轮都调用博查。案件分析的 `retrieval.case_search` 为 `not_requested` 时，表示本轮未请求联网检索。
- 请求的 `include` 使用官方要求的字符串，多域名以 `|` 分隔；返回后再次校验 HTTPS 与精确域名，仅接受 `tousu.sina.com.cn` 和 `anli.court.gov.cn`，不允许后缀伪装域名。
- 搜索词只发送匹配的通用主题词；未命中时发送通用消费纠纷查询，不直接发送整段案件描述。
- 白名单或搜索引擎收录范围可能使结果为空。接口返回的是搜索摘要和链接，不保证能直接读取目标站全文。
- 黑猫投诉属于投诉者陈述，不等于查证事实、裁判结果或法律依据。法院案例摘要也需核对原文与适用事实。
- 联网失败时保留本地法条检索能力，不编造案例。日志和自检不输出 API Key 或供应商原始异常内容。

核对来源（2026-11-15）：[博查官网示例](https://open.bochaai.com/)、[官网链接的 Web Search 文档](https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK)。
