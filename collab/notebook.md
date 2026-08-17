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

---

## 变更记录

### [2026-08-17 16:00] CodeBuddy/YAQH侧 · 初始化共享笔记本
- action: add | target: collab/notebook.md + collab/log.py
- desc: 建立双 agent 后台共享日志与读写助手，记录每次增删改及对应功能，供双方异步同步。
- note: 当前使用的 PAT 已在聊天中暴露，建议尽快 revoke 并换一把 scoped（仅 repo、设过期）token。

### [2026-08-17 16:00] CodeBuddy/YAQH侧 · 待同步的本地三处框架改进（尚未 push）
- action: modify | target: fetch_zn.py:fetch_news
- desc: 修复新闻拉取解析 bug（'str' object has no attribute 'get'），兼容 items/data/list/裸数组，跳过非 dict 元素。未改动任何评分/关键词/过滤规则。
- action: modify | target: contradiction_engine.py:run_engine + _dedup_by_series
- desc: 新增按底层序列去重，避免 lme_cancelled 同时填 A1.cancelled 与 B11.outflow 被计两次矛盾。
- action: add | target: fetch_zn.py:main -> data["active_contradictions"]
- desc: 每次流水线写入实时矛盾种子字段（structured+formatted），供前端 A/B 图表自动重排消费。
- note: 以上三处为本地改动，待用户确认后由本 agent push；新闻拉取/AI文本/部署仍依赖 Hermes 的密钥与服务器。zhiji 新闻 API 严格限流，勿频繁调用。

### [2026-08-17 14:34] CODEBUDDY · ADD
- target: collab/log.py:add_entry
- desc: 绔埌绔獙璇佸叡浜瑪璁版湰杩藉姞鎺ュ彛鍙敤
- note: Hermes 渚у彲鐢ㄥ悓鏂瑰紡杩藉姞/璇诲彇锛屾棤闇€ git CLI
