# 锌看板 · GitHub 架构 / 板块关联 / 权限边界 交接文档

> 读者：接手本仓库的任意 agent（含未来的 CodeBuddy / Hermes / 新会话）
> 维护：CodeBuddy/YAQH 侧（本机，无 git CLI，用 `collab/push.py` 经 GitHub Contents API 读写）
> 最后更新：2026-08-17

---

## 0. 一句话架构

本地文件 ≡ GitHub 仓库文件（路径一一对应）。`main` 分支既是**网站源码**也是**数据枢纽**。两个 GitHub Actions 工作流构成自动流水线：

```
[Zhiji Guan/料/News API + akshare 宏观]
        │  (fetch.yml 每 30 分钟在云 runner 跑 python fetch_zn.py)
        ▼
fetch_zn.py 拉数据 → gen_analysis(规则) + run_engine(矛盾引擎) + gen_ai(AI解盘)
        │  写 data.json（charts / ai_analysis / active_contradictions / cross_check）
        ▼
git commit & push main
        │  (main 被 push 触发 deploy.yml)
        ▼
GitHub Pages 部署静态站 → https://algo23-yunqingtian.github.io/zinc-dashboard/
        │
        ▼
index.html / charts.js 从 Pages 的 data.json 读取并渲染
```

**关键结论（常被误判）**：AI 解盘 **不在** Hermes 的 ubuntu 服务器手动跑，而是 `fetch.yml` 在 GitHub Actions 云上每 30 分钟自动跑。任何 push 到 `main` 的代码改动，下一次 `fetch.yml` 触发（≤30 分钟）即自动生效，**不需要任何人手动 `git pull`**。

---

## 1. 本地 ↔ GitHub 网址 映射机制

| 概念 | 说明 |
|---|---|
| 仓库 | `algo23-yunqingtian/zinc-dashboard`，分支 `main` |
| 本地文件 → 仓库文件 | 路径完全一致。例：本地 `analyze_zn.py` ≡ 仓库 `analyze_zn.py`；本地 `docs/ROADMAP.md` ≡ 仓库 `docs/ROADMAP.md` |
| 推送工具 | `collab/push.py`（无 git CLI 时用）。原理：GitHub Contents API —— GET 取现有 `sha` → base64 编码本地内容 → PUT 更新（带 sha 防冲突，409 自动重试）。token 仅从环境变量 `GITHUB_TOKEN` 读取。 |
| 用法 | `set GITHUB_TOKEN=ghp_xxx; python collab/push.py <本地路径> <仓库路径> "<message>"` |
| 网站 URL | GitHub Pages，由 `deploy.yml` 部署。默认 `https://algo23-yunqingtian.github.io/zinc-dashboard/`（若仓库设了自定义域名则用自定义域名，以 `deploy.yml` 的 `github-pages` 环境 URL 为准） |

---

## 2. 各板块（工作流 / 文件）职责与数据关联

### 2.1 工作流（`.github/workflows/`）
- **`fetch.yml`** — 触发器：`cron '*/30 * * * *'`（每30分钟）+ `workflow_dispatch`（手动）。在 `ubuntu-latest` 跑：
  1. checkout 最新 main
  2. 注入密钥到环境变量：`ZHJI_KEY / GUAN_KEY / NEWS_KEY / DATA_KEY`（来自 `secrets.*` 或 inline 默认占位）、`ZSUN_KEY / DASHSCOPE_KEY / DASHSCOPE_MODEL / SILICONFLOW_KEY`
  3. `pip install -r requirements.txt`
  4. `python fetch_zn.py`
  5. `git add data.json && git commit && git push`
- **`deploy.yml`** — 触发器：`push` 到 `main` + `workflow_dispatch`。把整个仓库作为静态站点 `upload-pages-artifact` → `deploy-pages`。

> 数据刷新频率 = `fetch.yml` 频率（≤30 分钟）。改提示词/引擎代码 = push 到 main → 下次 fetch 自动用新代码。

### 2.2 核心 Python 文件（数据枢纽 `data.json` 的读写方）
| 文件 | 职责 | 关键调用 |
|---|---|---|
| `fetch_zn.py` | **中枢**。拉数据→组装 18 图 charts→三条分析→写 `data.json`→（由 Actions）push | `gen_analysis()` 规则多空；`run_engine()` 矛盾引擎；`gen_ai()` AI 解盘 |
| `analyze_zn.py` | 被 `gen_ai` 调用，专管 **prompt 构建 + AI 调用**。含 `build_prompt_active`（默认 v2）→ `build_prompt_v2` → `_v2_prompt_template`；含独立 `call_ai`（但生产用 fetch_zn 的 call_ai） | `build_prompt_active(charts,news,reports,macro)`；`analyze()`（独立入口） |
| `contradiction_engine.py` | L2 矛盾引擎：rule / anomaly / divergence 三策略 + `_signal_direction` 数据代理方向 | `run_engine(charts, news)` → `format_for_prompt()` |
| `zinc_scoring.yaml` | 9 条核心矛盾框架 + 每条的 `signal` 数据代理方向配置 | 被 `_load_contradiction_framework()` 与 `_signal_direction()` 读取 |
| `scorer_v2_zn.py` | 新闻打分/相关性闸门 | 被 `fetch_zn.fetch_news()` 调用 |
| `indicator_lib.py` | 指标标准化、序列提取（`SERIES_REGISTRY` 短键→长键） | 被 `contradiction_engine` 与 `analyze_zn` 调用 |
| `index.html` / `charts.js` | 前端，从 Pages 的 `data.json` 读取渲染 | 消费 `charts` / `ai_analysis` / `active_contradictions` |

### 2.3 `data.json` 字段（前后端唯一枢纽）
`charts`(18图) · `news`(items+highlights) · `analysis`(规则多空) · `ai_analysis`(AI解盘文本) · `cross_check`(规则vsAI) · `realtime` · `macro` · `active_contradictions`(L2矛盾,供前端自动重排) · `prompt_data` · `prompt_version` · `data_sources`(溯源:Zhiji/akshare)。

---

## 3. AI 解盘（gen_ai）全链路与"产出质量"的所有变量

```
fetch_zn.gen_ai(charts, news, macro)
   └─ analyze.build_prompt_active(默认 PROMPT_VERSION=v2)
        └─ build_prompt_v2(...)  ← 我改的"强指令"在此(_v2_prompt_template 末尾 "机器强制方向指令"段)
   └─ call_ai(url, key, model)  ← fetch_zn 内部实现：zsun → DashScope → SiliconFlow
        payload: {model, messages:[system, user], max_tokens:4096, temperature:0.7}
```
- system prompt：`"你是专业锌期货分析师，输出结构化研报。"`
- 模型顺序：`ZSUN`(Qwen36_35B, zsun.funkits.cn) 主 → `DashScope`(qwen3.7-max, 阿里百炼) 备 → `SiliconFlow` 备用。
- 注意：Actions 的 `fetch.yml` 仅显式传入 `DASHSCOPE_KEY/SILICONFLOW_KEY`，`ZSUN_KEY` 仅 echo 到 `$GITHUB_ENV`；若 `secrets.ZSUN_KEY` 为空则 Actions 上走 DashScope/SiliconFlow。

**影响 AI 解盘产出质量的变量（穷尽，无隐藏第 8 类）：**
| # | 变量 | 我能改吗 | 说明 |
|---|---|---|---|
| 1 | 输入数据（18 指标数值+派生） | ⚠️ 受限 | 内容来自 Zhiji/akshare 外部 API，改不了真实值；可改"哪些进 prompt / 映射 / prefilter 阈值 / 派生计算"（indicator_lib、fetch_zn charts 组装） |
| 2 | 输入新闻 | ⚠️ 受限 | 内容来自 Zhiji News API，改不了；可改"筛选/打分/去噪"（scorer_v2_zn、analyze_zn._EXCLUDE_NOISE/_HIGH_WEIGHT_KW、fetch_zn.fetch_news 闸门） |
| 3 | 提示词模板 | ✅ 完全可控 | analyze_zn.build_prompt_v2 / _v2_prompt_template + zinc_scoring.yaml 矛盾框架。改完 push 即生效 |
| 4 | 矛盾引擎注入方向 | ✅ 完全可控 | contradiction_engine + zinc_scoring.yaml 的 signal 配置；已做"强指令"让模型优先采纳 |
| 5 | 模型 + 参数 | ⚠️ 部分 | 只能选模型（环境变量）和改代码里的 `temperature`/`max_tokens`；不能改模型权重 |
| 6 | 动态权重算法 | ✅ 可控 | analyze_zn 按波动率算供需/库存/需求/资金权重（weight_note），在代码内 |
| 7 | 数据新鲜度 | — | 由 fetch.yml 每30分钟保证 |

> 结论：**提示词(3) 与 引擎方向(4) 是我能 100% 掌控、且改动即时生效的两个杠杆**；数据与新闻(1)(2) 我只能调"如何被使用"，调不了来源本身；模型(5) 基本固定。

---

## 4. 权限边界矩阵（谁能改什么）

| 能力 | CodeBuddy/YAQH（本机，classic PAT repo 权限） | Hermes（腾讯云/ubuntu） |
|---|---|---|
| push/pull GitHub 仓库 | ✅ 用 `collab/push.py` | ✅（同仓库协作者） |
| 改提示词/引擎/配置代码 | ✅ 改完 push 即生效（Actions 自动用） | ✅ |
| 改 GitHub Actions secrets（密钥） | ❌ 在 repo Settings，需 admin/owner | ✅（看其角色） |
| 改 `fetch.yml`/`deploy.yml` 触发配置 | ✅ 改 yaml 后 push（我有 repo 写权限） | ✅ |
| 跑 AI 解盘（生产） | 自动（Actions）无需人为跑 | 也可在 ubuntu 手动跑 analyze_zn 推飞书/微信 |
| 访问 Hermes 的 `/home/ubuntu` 服务器 | ❌ 无 SSH/访问权 | ✅ 那是他机器 |

**关于"为什么只有 Hermes 能 git pull"——前提不成立**：
- GitHub 仓库层面，我和 Hermes **都能** push/pull。我一直在用 push.py 推代码。
- 生产 AI 解盘在 GitHub Actions 自动跑，Actions 自己 checkout 最新 main，**我 push 后 ≤30 分钟自动生效，无需任何人手动 git pull**。
- 唯一需要 Hermes 的：若他在自己 ubuntu 服务器上另跑一份（analyze_zn 的 `GH_STATIC_DATA="/home/ubuntu/..."` 是历史默认路径，指向那台机器）用于推飞书/微信，那台机器只有他有访问权。但**面向网页前端的 AI 解盘不依赖他**。若你看到的解盘"变化慢"，通常是数据本身没变（变量 1/2），而非部署未同步。

---

## 5. 给其他 agent 的"上手清单"
1. 想改 AI 解盘文本质量 → 改 `analyze_zn.py` 的 `build_prompt_v2`/`_v2_prompt_template`（或 `zinc_scoring.yaml` 矛盾框架）→ `python collab/push.py analyze_zn.py analyze_zn.py "msg"`。
2. 想改机器矛盾识别 → 改 `contradiction_engine.py` + `zinc_scoring.yaml` 的 `signal` → push。
3. 想验证本地效果（0 次 API）→ `python collab/screen_zinc.py`（跑引擎）、`python -c "from analyze_zn import build_prompt_v2; ..."`（看 prompt 文本）。
4. 想立刻刷新线上数据/解盘 → 在 GitHub 仓库 Actions 页手动 `workflow_dispatch` 触发 `fetch.yml`（不必等 30 分钟）。
5. 不要碰：`secrets` 密钥（在 repo Settings）、Hermes 的 ubuntu 机器、`.env`（服务器侧）。
6. 本机无 git CLI，统一用 `collab/push.py`（读 `GITHUB_TOKEN` 环境变量）；协作日志写 `collab/notebook.md`。
