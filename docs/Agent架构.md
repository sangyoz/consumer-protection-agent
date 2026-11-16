# 当前 Agent 架构：动态决策与防幻觉

依据 2026-11-15 工作区代码与本地配置绘制。实线表示当前可用流程；灰色虚线节点表示已实现接口、尚未配置的可选能力。

```mermaid
flowchart TD
    U["用户输入<br/>案件描述 · 商家回复 · 投诉草稿请求"] --> API["FastAPI 业务接口"]
    API --> S["AgentState 全局状态<br/>案情 / 对话 / 证据清单 / 策略 / 检索结果 / 审计记录"]

    subgraph D["动态决策：LangGraph 条件边与工具循环"]
        S --> E["证据盘点<br/>区分缺失、已上传未核验、用户自述"]
        E --> P["DeepSeek 决策 + Pydantic 校验<br/>输出 action / tools / query"]
        P --> R{"需要检索且未超过工具预算？"}
        R -->|"是：按需选择工具"| T["受控工具调度<br/>最多 2 轮，同一检索器每次运行最多调用 1 次"]
        T --> L["本地法律检索<br/>SQLite：1,412 条 · BM25 已启用"]
        T -.-> V["可选：向量检索 + BM25<br/>RRF 融合；尚未配置 Embeddings"]
        T -.-> W["可选：博查案例检索<br/>尚未配置 API Key<br/>域名白名单 + 返回 URL 过滤"]
        L --> O["Observation 检索结果<br/>法条原文 / 来源 / 案例类型 / 检索状态"]
        V -.-> O
        W -.-> O
        O -->|"更新状态，再次决策"| P
        R -->|"不需要或已达预算"| A{"策略条件路由"}
        A --> C["补充证据"]
        A --> N["继续协商"]
        A --> X["升级处理建议"]
        A --> Q["投诉草稿<br/>仅限用户主动请求"]
    end

    C --> G
    N --> G
    X --> G
    Q --> G

    subgraph H["防幻觉：约束生成、引用审计与自我修正"]
        G["约束生成 + JSON 结构校验<br/>仅使用本轮法条；案例与法律分离<br/>无依据不编造法条，无密钥或调用失败则本地回退"]
        G --> K{"代码级引用审计"}
        K --- K0["本轮召回且仍在库内有效？<br/>法律名与条号匹配？<br/>结构化引文与原文逐字匹配？<br/>链接属于对应来源？"]
        K -->|"未通过，且尚未修正"| F["生成校验反馈<br/>记录问题并自动重写 1 次"]
        F -->|"保持当前策略，重新生成"| G
        K -->|"重写后仍未通过"| B["安全回退<br/>丢弃模型原稿，输出无引用的保守建议"]
        K -->|"通过"| Z["整理结果<br/>附已匹配引文与来源，保留审计轨迹"]
        B --> Z
    end

    Z --> DB["保存案件状态<br/>证据清单 · 策略 · trace · 修正记录 · 实际引擎"]
    DB --> UI["前端展示<br/>建议与话术 / 用户核对后自行处理"]
    UI -.->|"下一轮补充信息或商家回复"| U

    classDef decision fill:#eaf2ff,stroke:#3775c6,color:#173c6b;
    classDef retrieval fill:#e9f6ef,stroke:#43845d,color:#214e33;
    classDef guard fill:#fff4df,stroke:#bd862a,color:#6b4a14;
    classDef fallback fill:#fcecec,stroke:#ba5555,color:#7b3030;
    classDef optional fill:#f6f7f9,stroke:#9299a7,color:#596170,stroke-dasharray:5 5;
    class S,E,P,R,T,A,C,N,X,Q decision;
    class L,O retrieval;
    class G,K,K0,F,Z guard;
    class B fallback;
    class V,W optional;
```

## 动态决策

- 决策依据包含案情、最近对话、上一轮策略、证据状态及本轮工具观测；模型选择动作和检索工具，由代码约束合法值。
- 核心交易或付款证据不足时优先补证；投诉文书只在用户主动请求投诉草稿时生成。
- 检索后进入 decide 节点再次判断。工具轮次最多两轮，每个检索器同次工作流只调用一次；引用自修正最多一次。
- 案件层持久化部分状态和 trace，并在后续请求中重建 AgentState；当前未使用 LangGraph checkpointer，不等于图内断点续跑。

## 防幻觉边界

- 本地法条与联网案例用途分离，黑猫投诉属于投诉人陈述，不能当成法院认定或法律依据。
- 提示词要求仅依据召回原文作答；Pydantic 约束 JSON 结构，引用审计核对本次召回条文、条号、来源和结构化引文。
- 修正仍失败时丢弃模型稿，保留错误历史并输出不含法条引用的固定建议。
- 来源匹配不等于法律适用正确。正则与逐字校验不能验证所有释义和事实；不应宣称“彻底消除幻觉”或“准确率 100%”。
- 法律原文来自本地下载文件，来源和版本日期由用户提供；尚未对官方全文逐条比对。
- 证据仅有上传元信息和用户自述，尚无 OCR、正文理解或真实性核验。

## 当前配置

- 本地法律库：1,412 条，BM25 可用。
- 向量与 BM25 的 RRF 混合检索：代码已实现，未配置 Embeddings。
- 博查白名单案例检索：代码已实现，未配置 BOCHA_API_KEY。
- 模型错误或 JSON 校验失败：使用本地回退，并记录实际 engine。

## 对应代码

- backend/app/agents/workflow.py：状态与条件边、工具循环、引用修正和安全回退。
- backend/app/services/agent.py：决策/生成提示词、JSON 校验、动作约束及模型失败回退。
- backend/app/services/retrieval.py：BM25、向量融合、案例白名单和引用核对。
- backend/app/services/evidence.py：证据状态盘点。
- backend/app/main.py：接口与案件状态持久化。
