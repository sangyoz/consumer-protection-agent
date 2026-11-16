# 有理 消费维权助手代码框架

这是供两人分模块继续开发的前后端骨架。页面按文件夹中的设想图组织，使用蓝白色卡片风格、案件列表和可折叠的三栏工作台。

## 一键启动

需要 Node.js 20.19+、Python 3.10+ 和 Windows PowerShell。第一次启动会创建 `backend/.venv`、安装前后端依赖、生成本地 `backend/.env`，然后同时启动 FastAPI 和 Vue，默认连接 SQLite：

```powershell
双击 start.bat
```

也可以在项目根目录选择 MySQL：

```powershell
.\start.bat -Database mysql
```

MySQL 模式需要启动 Docker Desktop。脚本会运行 `docker compose up -d --wait mysql`，数据库保存在持久化 Docker volume。停止应用不会关闭容器或删数据。单独停止容器使用 `docker compose stop mysql`；重置数据库卷需要手动使用 `docker compose down -v`，该命令会删除数据。

前后端地址分别为 http://127.0.0.1:5173 和 http://127.0.0.1:8000/docs。一键启动总是连接后端 API；默认 Agent 通过 LangGraph 编排本地演示规则。日志保存在 `.run/logs/`。双击 `stop.bat` 停止，或运行 `npm run status` 查看状态。`start.ps1 -Action start -Database sqlite|mysql` 支持同样操作。

## LangGraph Agent

Agent 入口在 `backend/app/agents/workflow.py`，提示词、结构化模型输出与决策约束在 `backend/app/services/agent.py`，证据盘点在 `backend/app/services/evidence.py`，法律/案例检索与法条来源审计在 `backend/app/services/retrieval.py`。

工作流按“证据盘点 → LLM 决策 → 条件边选择补证/协商/升级/投诉 → 选择性检索 → 观察检索结果并再次决策 → 草拟 → 法条审计 → 最多自我修正一次 → 安全回退”运行。LangGraph 的执行 trace、策略、检索状态与引用审计结果随案件保存。模型只返回受 Pydantic 约束的 JSON；工具调用由代码白名单调度，没有执行模型生成的代码。工具最多调用两轮，各检索器同一次案件调用中只执行一次。

DeepSeek 聊天模型设置仍在 `backend/.env`：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`。配置后重启后端。密钥只说明已配置；单次请求若模型失败或 JSON 校验失败，会使用本地安全回退并把实际 `engine` 标记为 `demo`。消费纠纷文本可能发往模型服务，建议先避免提交姓名、电话、证件号、订单号等个人信息。

### 法律库与检索

法条库是独立的 `backend/legal.sqlite3`，避免数据库选择 MySQL 时改变法律语料位置。仓库不附带未经核对的法律文本。使用前从国家法律法规数据库等官方来源自行整理 UTF-8 JSONL，每行至少包含 `id`、`law_name`、`article`、`content`、`source`、`effective_from`、`reviewed_at`，可选 `effective_to`。来源必须为 `flk.npc.gov.cn`、`npc.gov.cn` 或 `gov.cn` 的 HTTPS 链接，条文需由维护者核对并记录复核日期。设置 `LAW_CORPUS_PATH` 指向该文件，启动时导入；或运行 `backend/.venv/Scripts/python.exe -m app.services.retrieval path/to/laws.jsonl`（工作目录 `backend`）。示例行：

```json
{"id":"law-article-id","law_name":"法律全名","article":"55","content":"从官方来源逐字核对的完整原文","source":"https://flk.npc.gov.cn/...","effective_from":"2024-07-01","reviewed_at":"2026-01-01"}
```

当前检索组合本地 BM25 关键词排序与可选向量余弦相似度，以 Reciprocal Rank Fusion 合并。向量检索需要额外配置兼容 OpenAI Embeddings 的独立 `EMBEDDING_API_KEY`、`EMBEDDING_MODEL`，可选 `EMBEDDING_BASE_URL`；DeepSeek 聊天密钥不自动提供向量能力。未配置向量服务时返回 BM25 模式，不会谎称混合检索已启用。

联网案例检索可设置 `BOCHA_API_KEY` 与 `BOCHA_BASE_URL`。查询内容被压缩为预设的纠纷类别关键词，返回结果还要经 HTTPS 主机名检查，只保留 `tousu.sina.com.cn` 和 `anli.court.gov.cn`；黑猫投诉内容会标记为投诉人陈述，而非认定事实。未配置或服务故障都会在案件检索状态中区分显示。

引用审计限制模型只能引用本轮召回且仍有效的法条 ID，并要求引用原文为库内连续原文；链接限制为对应官方来源。校验的是来源身份和引文，不代表系统确认该法条适用于本案。缺少语料时会明确无已核验依据。用户上传的证据目前只保存文件，证据状态清单不会声称系统已检查附件内容。

生产构建检查：

```powershell
npm.cmd run build
```

## 手动启动

如需单独调试模块，可分别运行前后端。

需要 Python 3.10+。打开第二个终端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

接口文档：http://127.0.0.1:8000/docs 。默认使用 SQLite 自动创建 `backend/youli.db`，不需要先安装 MySQL。后续复制 `backend/.env.example` 为 `.env`，修改 `DATABASE_URL`，即可使用已建好的 MySQL 8 数据库。

前端连接方式：复制 `frontend/.env.example` 为 `frontend/.env`，将 `VITE_DATA_MODE` 改成 `api`，重启前端。Vite 将 `/api` 转发到 8000 端口。后端初始列表为空；本地模拟数据和后端数据相互独立，不自动迁移。

## 目录与分工

```text
frontend/src/
  App.vue                       共用导航和应用布局
  views/                        案件中心、新建、工作台、跟进、个人中心
  components/workbench/         分析、协商、投诉、其他方案模块
  api/                          统一接口入口、模拟实现、演示数据
  stores/                       Pinia 案件状态
  domain/                       案件阶段与共享定义
  styles/                       公共设计变量、页面样式
backend/app/
  main.py                       FastAPI 接口与请求协调
  schemas.py                    请求结构校验
  database.py                   SQLAlchemy 数据与数据库配置
  services/agent.py             模拟分析和沟通建议，真实 Agent 替换入口
  services/complaint.py         根据已有案件信息整理投诉草稿
  agents/workflow.py            LangGraph 工作流扩展位置
docs/                           模块约定和接口说明
```

建议 A 负责案件创建、证据与分析诉求，B 负责沟通协商、投诉与处理跟进。每人负责自己业务模块的页面、接口和服务；`frontend/` 与 `backend/` 是运行结构，不是人员分工。先共同确认案件字段与接口约定，再按模块扩展。

## 当前范围

- 已实现：页面路由、统一样式、案件创建、列表搜索与筛选、案件分析页、沟通记录、话术语气切换与复制、投诉草稿、附件入口、处理时间线与用户确认结案。
- 默认模拟模式：附件只记录文件名与大小，不保存文件内容；分析使用明确标注的模拟规则。
- 后端模式：案件持久化到数据库，附件保存到 `backend/uploads/`，尚未执行 OCR 或文档解析。
- 预留：DeepSeek、LangGraph、官方法律检索、OCR、多模态、真实流式输出、渠道推荐、外部平台辅助填表。
- 尚无账户认证、案件权限隔离和生产部署配置，定位为本机课程项目开发骨架。
- 当前不向商家或投诉平台发送信息；法律来源未接入，页面不输出已核验法律结论。结案需要用户确认实际履行。

测试依赖 `httpx` 已列入后端依赖安装流程，手动建立环境时执行：

在 `backend` 目录运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试使用内存数据库和临时上传目录，不修改正式案件。

详细分工和扩展边界见 `docs/开发框架.md`，接口见 `docs/接口约定.md`。
