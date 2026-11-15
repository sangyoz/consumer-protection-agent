# 法律原文转换

原始 TXT 放在本目录的 `raw/` 中。在项目根目录执行：

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\convert_laws.py
```

也可使用已安装的 Python 3.10+，脚本仅依赖标准库：

```powershell
python .\backend\scripts\convert_laws.py
```

脚本支持行首的 `第一条 正文` 和 `《法律名》第一条规定，正文`，将中文条号转换为阿拉伯数字，保留多款正文，分离编/章/节标题。重复条号会报错，不自动覆盖；现有法律库不支持“条之一”，遇到时会明确停止，避免合并或丢弃。TXT 编码自动识别 UTF-8/BOM、UTF-16 BOM、GB18030，可通过 `--encoding` 指定。

默认输出：

- `laws.draft.jsonl`：每行一个法条，包含文件名、原始行号与文件 SHA256，便于定位和复核。
- `metadata.json`：每个原始文件一份配置。首次运行自动创建，后续运行保留已填字段。
- `conversion_report.json`：每份文件识别的条数、缺失元数据和条号缺口等提示。
- `laws.jsonl`：所有文件的必填元数据完整且格式校验通过后才生成。元数据不完整时保留以前的正式输出，不更新；不会自动导入数据库。

请在 `metadata.json` 中补齐每个文件对应的：

| 字段 | 含义 |
|---|---|
| `law_name` | 法律全名，默认由 TXT 文件名取得 |
| `source` | 你核对的具体官方法律原文页面的 HTTPS 地址 |
| `effective_from` | 该文件所用法律版本的生效日期，YYYY-MM-DD |
| `reviewed_at` | 你实际核对官方原文的日期，YYYY-MM-DD |
| `effective_to` | 该版本失效日期；仍有效时保留 null |

不能把旧版本末条“本法自某日起施行”的日期直接当成当前修订版本生效日期。脚本不推断日期，不联网改写原文，也不会把转换完成视为法律内容已核实。格式校验只证明字段齐全，不证明文本完整、版本正确或真实权威。

填写后重新执行转换命令，检查报告和生成的 `laws.jsonl`。确认无误后，在 `backend/.env` 设置：

```dotenv
LAW_CORPUS_PATH=data/laws/laws.jsonl
```

然后停止并重新启动后端。现有 `retrieval.import_laws` 会在启动时导入 JSONL；转换脚本本身不会修改 `.env` 或 `legal.sqlite3`。
