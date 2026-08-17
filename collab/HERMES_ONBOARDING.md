# 给 Hermes 的交接说明 · 锌看板双 Agent 协作机制

> 作者：YAQH 侧的 CodeBuddy agent（本机 Windows 侧）
> 时间：2026-08-17
> 目的：让你（Hermes / 腾讯云 = 原"微信端/哈宝"）接手锌看板时，清楚我们（CodeBuddy ↔ Hermes）现在的协作机制、我刚 push 了什么、以及你怎么配合我。

## 0. 一句话机制
**GitHub 仓库 = 我们唯一的共享大脑 + 真相源（source of truth）。** 我们不在同一进程、没有直连 API，靠"共同读写仓库"异步协作。代码以 `main` 分支为准；本地永远是副本。

## 1. 沟通总线（你看得到、我也看得到，后台不在看板 UI）
- `collab/notebook.md`：共享笔记本/日志。每次增删改都追加一条，字段 = 时间(UTC+8) | agent | 动作 | 目标(文件:函数) | 功能说明 | 自由沟通。
- `collab/log.py`：读写助手（你要的"数据接口/函数"），自带并发冲突重试。
  - 追加：`python collab/log.py add --agent HERMES --action modify --target "charts.js:autoRearrange" --desc-file desc.txt --note-file note.txt`
  - 读取：`python collab/log.py tail --n 20`
  - ⚠️ Windows 侧中文走 `--desc-file/--note-file`（UTF-8 文件）避免命令行乱码；你 Ubuntu 侧直接内联也行。
- `collab/push.py`：本机无 git CLI，统一用它（读 `GITHUB_TOKEN` 环境变量）把本地文件 PUT 到 GitHub Contents API，自带冲突重试。

## 2. 认证（重要）
- 用户已提供一个 **classic PAT**（ghp_...）给我，目前**双方共用同一把**。
- ⚠️ 这把 token **已在聊天记录里明文暴露**，强烈建议：用户去 GitHub 后台 revoke 它，换一把 **scoped（仅 repo 权限、设过期时间）** 的新 token；最好给我们各一把独立同权限 PAT，便于单独 revoke。
- 用法：本机 `set GITHUB_TOKEN=ghp_xxx`（PowerShell）后跑 push.py / log.py，**切勿把 token 写进任何文件或贴聊天窗口**。

## 3. 我刚 push 了什么（2026-08-17 17:30，main）
| 文件 | 改动 | 对应功能 |
|---|---|---|
| `fetch_zn.py` (`fetch_news`) | 修复解析 bug：`'str' object has no attribute 'get'`，兼容 items/data/list/results/裸数组，遇非 dict 元素跳过而非崩溃 | 新闻不再因返回结构异常而整段拉空，规则类矛盾不再丢失 |
| `contradiction_engine.py` (`run_engine` + `_dedup_by_series`) | 新增按底层序列去重 | 避免 `lme_cancelled` 同时填 `A1.cancelled` 与 `B11.outflow` 被计两次矛盾 |
| `fetch_zn.py` (`main`) | 每次流水线写入 `data["active_contradictions"]`（structured+formatted） | 供前端 A/B 图表按矛盾强度自动重排/高亮消费（即 `AUTO_REARRANGE_PROMPT.md` 的落地点） |
| `collab/log.py` | UTF-8 输出修复 + `--desc-file/--note-file` | 跨平台中文不崩、不乱码 |
| `collab/push.py`（新增） | 复用推送助手 | 双方都能无 git 推文件 |
| `collab/HERMES_ONBOARDING.md`（新增） | 本文件 | 交接说明 |

**这些只在 GitHub（含 GitHub Pages 缓存版）生效；你服务器版 `/home/ubuntu/zinc_dashboard_gh/` 需你自己 pull/rebase 才同步。**

## 4. 分工变化（请注意，跟旧文档不同了）
- `COLLAB_RULES.md`（v1.0）写的是"**仅微信端 push、飞书端禁改 fetch_zn.py**"。
- `collab/PROTOCOL.md` 写的是"CodeBuddy 负责 fetch_zn.py/analyze_zn.py/contradiction_engine.py，用 STATE/INBOX/OUTBOX" —— 但 STATE/INBOX/OUTBOX **从未实际创建**，实际落地的是 `notebook.md + log.py`。
- **当前真实模型（用户 2026-08-17 新授权）**：双 agent 都可用 PAT push；沟通总线 = `collab/notebook.md + collab/log.py`。建议你抽空把 `COLLAB_RULES.md` / `collab/PROTOCOL.md` 统一改成这个新模型，避免后来人困惑。

## 5. 你这边的待办（来自既有规划）
- 实现 `data.json.active_contradictions` 的前端消费：`charts.js` 动态排序/高亮（见 `AUTO_REARRANGE_PROMPT.md`）。
- 修 `lme_canc` ↔ `b11_out` 数据复用串列（两序列最新值/涨幅相同，疑似同源或回填串列）。
- 接入新闻让 rule 类矛盾真正生效（依赖你的 Zhiji/腾讯云 DB/akshare 与 AI 密钥）。
- 密钥安全：把 `GUAN_KEY/DATA_KEY/NEWS_KEY`（现硬编码在 public 仓库 fetch_zn.py）挪进 GitHub Actions Secrets 或 `.env`（不入库）。

## 6. 红线提醒
- **zhiji 新闻 API 严格限流**：勿频繁手动拉；生产保持 `fetch.yml` 每 30 分钟一次。`fetch_news` 一次内会调 6 次 zhiji（1 主搜 + 5 补充关键词），触限流就降频/减关键词。
- 绝不把 token/密钥写进 `collab/notebook.md` 或任何仓库文件。

## 7. 我们怎么"对话"
没有直连通道。要给我任务/指令：在 `collab/notebook.md` 追加一条（或直接在用户这边的对话里说，用户会转述）。我做完会在 notebook 追加结果。两边以 `tail` 对齐进度即可。

---
欢迎接手，有疑问在 notebook 留话，我看到就回。
