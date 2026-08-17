# 锌看板 · 双 Agent 协作笔记本 (Shared Notebook)

> 使用者：CodeBuddy / YAQH 侧 agent（本机） & Hermes / 腾讯云 agent
> 这是**后台共享日志，不在看板 UI 展示**。双方任何改动都在此追加一条，彼此可追踪"谁、何时、改了什么、对应什么功能"。
> 写入：`python collab/log.py add --agent <名> --action <add|remove|modify> --target <文件:函数> --desc "..." [--note "..."]`
> 读取：`python collab/log.py tail --n 20`
>
> ⚠️ 安全：只记录"做了什么"，**绝不在本笔记本写明文 token / 密钥**。认证走环境变量 `GITHUB_TOKEN`。

## 协议约定
- 每次改动前先 `tail` 看最新状态，避免重复/冲突。
- 字段：时间(UTC+8) | agent | 动作 | 目标 | 功能说明 | 自由沟通
- 加/减/改都记；涉及部署、密钥、数据源等敏感操作只记行为不记密文。
- 本机无 git CLI，统一用 `collab/log.py`（GitHub Contents API）读写本文件。
- 推送代码：本机无 git，用 `collab/push.py`（读 GITHUB_TOKEN 环境变量，PUT 到 Contents API，自带冲突重试）。

---

## 变更记录

### [2026-08-17 19:40] CodeBuddy/YAQH侧 · 架构研究 + 权限边界澄清（修正"需Hermes git pull"误判）
- action: research+doc | target: docs/ARCHITECTURE.md（新建）+ ROADMAP.md(引用)
- desc: 研究本地↔GitHub映射(push.py用Contents API按路径PUT)、fetch.yml(每30min Actions跑fetch_zn)→写data.json→push→deploy.yml部署Pages。确认AI解盘在Actions自动跑(gen_ai→analyze.build_prompt_active默认v2→build_prompt_v2)，**push即≤30min自动生效，不需Hermes手动git pull**。整理权限矩阵(我能改提示词/引擎/配置并push生效；不能改secrets/ubuntu机器)与AI解盘产出7变量(数据/新闻/提示词/引擎/模型/权重/新鲜度)。
- note: 修正前两条(18:10误报孤儿 / 19:20说"需Hermes重跑")——生产AI解盘是Actions自动，push即生效。模型顺序 zsun→DashScope→SiliconFlow, temperature=0.7, max_tokens=4096(fetch_zn.gen_ai内)。详见 docs/ARCHITECTURE.md。

### [2026-08-17 19:20] CodeBuddy/YAQH侧 · AI解盘强指令优化 + 根因澄清
- action: modify | target: analyze_zn.py(_v2_prompt_template 加 contra_directive + build_prompt_v2 生成强指令) + docs/ROADMAP.md(§2.1)
- desc: 用户反馈"改了引擎但 AI 解盘没变化"。定位根因：数据方向原本只注入辅助段(contra_inject)，模型主要信 18 指标数值段；且 AI 解盘部署在 Hermes ubuntu 服务器(ZSUN Qwen36_35B 主 / DashScope qwen3.7-max 备)，本机无 key 跑不了，需 git pull+重跑才生效。解法：V2 模板新增"机器强制方向指令"段，把 high-confidence 方向(direction≠0 & confidence≥0.6)以强指令注入，要求模型在结论优先采纳。本地 build_prompt_v2 实测注入成功。
- note: 模型未失效（失效会返回空/报错而非雷同文本）。代码已 push 到 main；要线上生效需 Hermes 重新跑 analyze_zn.py。详见 docs/ROADMAP.md §2.1。

### [2026-08-17 19:00] CodeBuddy/YAQH侧 · 数据代理方向层（矛盾识别不再依赖新闻措辞）
- action: modify | target: zinc_scoring.yaml(contradictions[].signal) + contradiction_engine.py(_signal_direction + _strategy_rule 接 charts) + docs/ROADMAP.md
- desc: 给 7 条数据可判矛盾加 signal{series,trend,direction} 配置；引擎新增 _signal_direction 用底层序列趋势补多空方向（新闻无方向时由数据兜底）。新建 docs/ROADMAP.md 总交接路线图。
- note: 实测本地快照：import_window(沪伦比↓→利空)、galvanizing_demand(镀锌产量↓→利空)、lme_squeeze(注销↑→利空) 由数据正确判出；tc/smelt_profit 快照 len=0(线上填满即生效)；inv_18 实为累库故不触发利多=正确行为。data vs news 结论：数据独立即可发现矛盾+方向，新闻仅贴语义标签。详见 docs/ROADMAP.md。

### [2026-08-17 18:40] CodeBuddy/YAQH侧 · lean 运维 + 框架澄清 + 接线误报更正
- action: add+verify | target: collab/screen_zinc.py, collab/notebook.md
- desc: 新增 token 极省运维脚本 collab/screen_zinc.py（纯本地0次Zhiji调用）：--explain 打印9条矛盾框架 / 空参跑引擎出实时命中 / --regen 用本地charts重算写回data.json。并用 --regen 刷新本地快照。
- note: **纠正前一条 18:10 误报**：搜索工具抽风读空壳目录，误判"引擎孤儿/未接线"。实测 fetch_zn.py:main(1087行)已调run_engine写active_contradictions(1160行)、analyze_zn.py(711-713行)已注入format_for_prompt。**接线早已完成**。本地 data.json 旧快照曾显False(旧版生成)，--regen 后写回7条、verify 现 STATE=True。引擎实跑筛选结果：1条[anomaly]lme_canc利空(强度1.0) + 6条[rule]新闻命中(矿端TC/冶炼/进口/镀锌/库存/政策)。divergence 0命中=需更长历史+校准锌特有配对阈值。详见 collab/screen_zinc.py 输出。

### [2026-08-17 17:30] CodeBuddy/YAQH侧 · PUSH 三处框架改动至 main
- action: push | target: fetch_zn.py, contradiction_engine.py, collab/log.py, collab/notebook.md, collab/push.py, collab/HERMES_ONBOARDING.md
- desc: 经用户授权，将本地三处改动（fetch_news 解析容错 / 矛盾引擎按序列去重 / data.json.active_contradictions 种子字段）push 至 GitHub main。新增 collab/push.py 复用推送助手、collab/HERMES_ONBOARDING.md 交接说明。
- note: 打破旧 COLLAB_RULES.md"仅微信端 push"约定；现双 agent 共用 PAT 均可 push，以 notebook 为沟通总线。Hermes 若服务器副本有未 push 改动需 rebase 到新 main。详见 collab/HERMES_ONBOARDING.md。

### [2026-08-17 16:00] CodeBuddy/YAQH侧 · 初始化共享笔记本
- action: add | target: collab/notebook.md + collab/log.py
- desc: 建立双 agent 后台共享日志与读写助手，记录每次增删改及对应功能，供双方异步同步。
- note: 当前使用的 PAT 已在聊天中暴露，建议尽快 revoke 并换一把 scoped（仅 repo、设过期）token。

### [2026-08-17 16:00] CodeBuddy/YAQH侧 · 本地三处框架改进（已于 2026-08-17 17:30 push 至 main）
- action: modify | target: fetch_zn.py:fetch_news
- desc: 修复新闻拉取解析 bug（'str' object has no attribute 'get'），兼容 items/data/list/results/裸数组，跳过非 dict 元素。未改动任何评分/关键词/过滤规则。
- action: modify | target: contradiction_engine.py:run_engine + _dedup_by_series
- desc: 新增按底层序列去重，避免 lme_cancelled 同时填 A1.cancelled 与 B11.outflow 被计两次矛盾。
- action: add | target: fetch_zn.py:main -> data["active_contradictions"]
- desc: 每次流水线写入实时矛盾种子字段（structured+formatted），供前端 A/B 图表自动重排消费。
- note: 以上三处已于 2026-08-17 17:30 经用户授权由本 agent push。新闻拉取/AI文本/部署仍需 Hermes 的密钥与服务器。zhiji 新闻 API 严格限流，勿频繁调用。
