# 有理 消费维权助手代码框架

这是供两人分模块继续开发的前后端骨架。页面按文件夹中的设想图组织，使用蓝白色卡片风格、案件列表和可折叠的三栏工作台。

## 先运行前端

需要 Node.js 20.19+ 或 22.12+。在项目根目录执行：

```powershell
npm.cmd install --prefix frontend
npm.cmd run dev
```

浏览器打开终端显示的本地地址，通常为 http://127.0.0.1:5173 。默认不需要启动后端；页面使用本地模拟数据，案件和沟通记录保存在当前浏览器中。初始提供两个演示案件，可创建新案件、生成演示分析、记录商家回复、生成投诉草稿和确认处理结果。

生产构建检查：

```powershell
npm.cmd run build
```

## 连接后端

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

## 后端验证

测试额外安装 `httpx` 后，在 `backend` 目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install httpx
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试使用内存数据库和临时上传目录，不修改正式案件。

详细分工和扩展边界见 `docs/开发框架.md`，接口见 `docs/接口约定.md`。
