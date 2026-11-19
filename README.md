# 有理 · 消费维权助手

面向消费纠纷的课程项目，使用 Vue 3、FastAPI、LangGraph 和 MySQL。用户可以整理证据、录入商家回复、获取沟通建议、准备投诉材料并记录处理结果。界面采用绿白配色，工作台按“材料 / 当前步骤交互 / 建议与进度”组织。两名成员按业务模块协作，每个模块可同时完善页面、接口和服务。

## 当前功能

- 注册、登录、退出与案件权限隔离，每个账号只能访问自己的案件。
- 首次创建时，Agent 从预设模块中选择并排列处理步骤，末步为“其他维权方式”。**生成后步骤数量和顺序固定**，后续材料、对话和反馈只更新内容与处理状态。
- 证据清单、材料上传与分类、经营主体核对、金额计算、沟通协商、平台介入、投诉准备、渠道核对、处理跟进及用户确认结案。
- 流程固定，当前分析和沟通建议仍结合新信息更新；“其他维权方式”可单独重新评估剩余办法，不修改步骤列表。
- 法条检索、联网案例检索、引用审计与有限反思修正；模型不可用时使用明确标注的规则回退。

系统不自动联系商家、提交投诉或接受和解。附件尚未接入 OCR、视频理解或内容真实性核验；上传和用户确认不等于系统已核实证据。

## 一键启动

需要 Node.js 20.19+、Python 3.10+ 和 Windows PowerShell。第一次启动会创建 `backend/.venv`、安装前后端依赖、生成本地 `backend/.env`，然后同时启动 MySQL、FastAPI 和 Vue：

```powershell
.\start.bat
```

默认使用 MySQL 8.4。没有已配置的 MySQL 时，脚本会从官方下载安装项目内的 Windows 版本（首次约 268 MB），无需 Docker 或管理员权限。本地服务只监听 `127.0.0.1:3306`，数据位于 `.run/mysql/data/`；随机密码保存在本机忽略目录与 `backend/.env`，不要提交或分享这些文件。**不要删除 `.run/mysql/`，其中包含业务数据库。**

首次切换时，自动备份 `backend/youli.db` 至 `.run/backups/` 并迁移案件，核对 JSON 内容一致；原 SQLite 文件和上传文件保留。同 ID 内容冲突时会中止，不覆盖目标数据。后续启动跳过迁移，避免旧库覆盖新进度。

**其他同学首次使用**：Windows 电脑安装好 Node.js、Python 后，下载或拉取最新版并运行 `start.bat` 即可，无需手动建库、导入 SQL 或安装 Workbench。脚本准备本机 MySQL，后台自动建立全部表。每台电脑的数据独立，不会共享本机账号、案件或 API Key；需用模型时自行在 `backend/.env` 配置密钥。首次下载 MySQL 和安装依赖需要网络。

若电脑已有 MySQL 占用 3306，脚本不会接管或覆盖它：请在 `.env` 配置自己创建的 `youli` 数据库和具有建表/改表/读写权限的账号，或先停止占用端口的实例。只运行 `npm run dev` 会启动前端，不会准备数据库或启动后端。注册 404 时确认后端 `/docs` 包含 `POST /api/auth/register`；一键启动会检查该接口以及前端代理是否正常。数据库不可用通常是启动失败或连接错误，不能仅凭 404 判断为数据库问题。

如确实需要独立的 SQLite 开发环境，可显式选择（它与 MySQL 之后的数据互不自动同步）：

```powershell
.\start.bat -Database sqlite
```

已有 MySQL 时，在 `backend/.env` 设置 `DATABASE_URL=mysql+pymysql://用户:密码@主机:3306/youli?charset=utf8mb4`，脚本优先连接该实例，不另装本地数据库。仓库也保留 `compose.yaml`：可自行运行 `docker compose up -d --wait mysql`，并使用文件中的开发账号配置连接。停止应用不会停止 MySQL 或删除数据库。

前端：http://127.0.0.1:5173 ；接口文档：http://127.0.0.1:8000/docs 。一键启动始终使用后端 API；配置 DeepSeek 后调用模型，否则通过 LangGraph 编排规则回退。日志保存在 `.run/logs/`。双击 `stop.bat` 停止前后端，或运行 `npm run status` 查看状态。健康检查 `/api/health` 检查数据库连接并返回实际数据库类型；`agentMode` 仅表示配置模式，单次请求的实际结果以案件 `engine`、`fallback_reason` 为准。

### 账号与登录

API 模式要求先登录。打开前端会进入登录页；新用户点击“注册账号”，账号为 3–32 位英文字母、数字或下划线，不区分大小写，密码为 8–128 位。密码只保存为 scrypt 哈希，浏览器使用 HttpOnly、SameSite 严格模式的会话 Cookie，默认有效期 7 天。案件接口按账号隔离（包括附件下载），未登录或过期返回 401，访问他人案件返回 404。

首次升级已有数据库时，原来的无归属案件会归入自动生成的初始账号。初始账号和密码写入本机 `.run/initial-account.txt`；该文件被 Git 忽略，不能上传。新注册账号从空案件列表开始。个人中心整合账号信息、资料表单与退出按钮；基本资料目前按账号保存在当前浏览器。

业务数据库现已按模块拆成案件、对话、材料、证据、步骤、跟进、时间线、流程元信息和分析文书等表；不再使用整案 `cases.payload`。已有库启动时自动备份、迁移并核对完整内容。字段、表关系和 Workbench 查询见 [数据库设计](docs/数据库设计.md)。

| 表 | 内容 |
| --- | --- |
| `users`、`user_sessions` | 用户账号与可注销的登录会话 |
| `cases` | 案件信息、金额、状态和账号归属 |
| `messages` | 商家回复与助手建议 |
| `materials` | 材料类型、文件名及存储信息 |
| `evidence_items` | 证据清单与确认状态 |
| `case_steps`、`case_plans` | 固定步骤、处理结果、流程元信息和替代方案 |
| `progress_records` | 渠道、受理状态与跟进记录 |
| `case_events` | 操作时间线 |
| `case_analyses` | Agent 分析、执行状态、投诉草稿与结案详情 |

业务库共 11 张表，子表通过 `case_id` 关联案件；动态分析和扩展信息保留 JSON。拆表迁移前会备份至 `.run/backups/`，逐案核对新旧完整对象后才移除旧列。上传原文件仍位于 `backend/uploads/`。

## LangGraph Agent

Agent 入口在 `backend/app/agents/workflow.py`，提示词、结构化模型输出与决策约束在 `backend/app/services/agent.py`，证据盘点在 `backend/app/services/evidence.py`，法律/案例检索与法条来源审计在 `backend/app/services/retrieval.py`。

案件级规划在 `backend/app/services/planning.py`，只在首次创建时运行。当前建议的动态分析与页面流程规划相互独立，“其他维权方式”的刷新使用独立输出结构，不允许新增、删除或重排步骤。

工作流按“证据盘点 → LLM 决策 → 条件边选择补证/协商/升级/投诉 → 选择性检索 → 观察检索结果并再次决策 → 草拟 → 法条审计 → 最多自我修正一次 → 安全回退”运行。LangGraph 的执行 trace、策略、检索状态与引用审计结果随案件保存。模型只返回受 Pydantic 约束的 JSON；工具调用由代码白名单调度，没有执行模型生成的代码。工具最多调用两轮，各检索器同一次案件调用中只执行一次。

DeepSeek 聊天模型设置仍在 `backend/.env`：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`。配置后重启后端。密钥只说明已配置；单次请求若模型失败或 JSON 校验失败，会使用本地安全回退并把实际 `engine` 标记为 `demo`。消费纠纷文本可能发往模型服务，建议先避免提交姓名、电话、证件号、订单号等个人信息。

### 法律库与检索

法条库是独立的 `backend/legal.sqlite3`，不随业务库 MySQL 切换。仓库包含整理后的 JSONL 语料及来源元数据，使用者仍需核对法律版本、原文和复核日期。每行至少包含 `id`、`law_name`、`article`、`content`、`source`、`effective_from`、`reviewed_at`，可选 `effective_to`。来源必须为官方白名单 HTTPS 链接。设置 `LAW_CORPUS_PATH=data/laws/laws.jsonl`（相对于 backend）后启动时导入；也可在 backend 目录执行 `.venv/Scripts/python.exe -m app.services.retrieval data/laws/laws.jsonl`。TXT 转 JSONL 脚本和元数据填写方式见 [法律原文转换](backend/data/laws/README.md)。示例格式：

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

接口文档：http://127.0.0.1:8000/docs 。首次请先运行 `start.bat` 完成 MySQL 初始化与旧案件迁移，之后可按上面的命令单独调试后端。也可自行创建 MySQL 数据库，在 `backend/.env` 配置 `DATABASE_URL`。

前端连接方式：复制 `frontend/.env.example` 为 `frontend/.env`，将 `VITE_DATA_MODE` 改成 `api`，重启前端。Vite 将 `/api` 转发到 8000 端口。后端初始列表为空；本地模拟数据和后端数据相互独立，不自动迁移。

## 目录与分工

```text
frontend/src/
  App.vue                       共用导航和应用布局
  views/                        登录注册、案件中心、新建、工作台、跟进、个人中心
  components/workbench/         分析、协商、投诉、其他方案模块
  api/                          统一接口入口、模拟实现、演示数据
  stores/                       案件状态、账号会话
  domain/                       案件阶段与共享定义
  styles/                       公共设计变量、页面样式
backend/app/
  main.py                       FastAPI 接口与请求协调
  schemas.py                    请求结构校验
  database.py                   SQLAlchemy 数据与数据库配置
  auth.py                       注册、登录、会话校验与退出
  services/agent.py             模型调用、结构化输出与提示词
  services/planning.py          首次流程规划与剩余办法建议
  services/case_repository.py   关系表与接口对象转换
  services/schema_migration.py  旧整案 JSON 拆表迁移
  services/retrieval.py         法条、案例检索与引用审计
  services/complaint.py         根据已有案件信息整理投诉草稿
  agents/workflow.py            LangGraph 单轮动态决策、审计与修正
backend/tools/                  MySQL 初始化与只读查库工具
docs/                           模块约定和接口说明
```

建议 A 负责案件创建、证据与分析诉求，B 负责沟通协商、投诉与处理跟进。每人负责自己业务模块的页面、接口和服务；`frontend/` 与 `backend/` 是运行结构，不是人员分工。先共同确认案件字段与接口约定，再按模块扩展。

## 当前范围

- 一键启动使用 API 模式，案件写入 MySQL 关系表，附件保存到 `backend/uploads/`。
- 手动运行前端时，`frontend/.env` 未配置 `VITE_DATA_MODE=api` 则使用独立 mock：数据保存在浏览器，附件只保存名称和大小，不具备后端账号权限隔离，也不会同步到 MySQL。
- 已接入 DeepSeek、LangGraph、本地法条检索与 Bocha 白名单案例检索；调用是否成功及降级原因会随案件显示。
- 尚未实现 OCR、多模态附件理解、真实流式输出、外部平台自动提交与生产部署配置。
- 来源和引用审计不等于确认法律适用，也不保证维权成功。结案仍需要用户确认实际履行。

测试依赖 `httpx` 已列入后端依赖安装流程，手动建立环境时执行：

在 `backend` 目录运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

普通测试使用临时数据库和上传目录，不修改正式案件。MySQL 专项测试默认跳过，需要设置 `MYSQL_TEST_URL` 指向独立的 `youli_test_*` 测试库；不要指向业务库。测试覆盖账号隔离、接口操作、关系表读写、迁移完整性、流程固定和引用审计。

在 backend 目录执行 `.\.venv\Scripts\python.exe tools\dump_db.py` 可只读查看当前库的表数量，追加 `cases` 或 `cases --full` 查看案件；`--db youli.db` 专用于查看旧 SQLite 备份。

详细分工和扩展边界见 `docs/开发框架.md`，接口见 `docs/接口约定.md`。
