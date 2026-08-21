# 协作协议 (collab/PROTOCOL — 现实对齐版)

> 旧版 PROTOCOL.md 描述的 `STATE.md / INBOX.md / OUTBOX.md` **并未实际创建**，属规划残留。本文说明真实落地机制。

## 真实落地的三件套（均在 `collab/`）
1. **`notebook.md`** — 共享笔记本（人类可读的变更日志）。双方每次增删改都追加一条。
2. **`log.py`** — 读写助手。
   - 追加：`python collab/log.py add --agent HERMES --action modify --target "charts.js:autoRearrange" --desc-file desc.txt --note-file note.txt`
   - 读取：`python collab/log.py tail --n 20`
   - 并发冲突（HTTP 409）自动重试；Windows 侧中文用 `--desc-file/--note-file` 读 UTF-8 文件。
3. **`push.py`** — 无 git 推送助手（GitHub Contents API，自带冲突重试）。
   - `python collab/push.py <本地路径> <仓库路径> "<commit message>"`，token 走环境变量 `GITHUB_TOKEN`。

## 健康探针
- **`verify_active_contradictions.py`** — 离线校验"自动矛盾识别"是否接通。定期跑一遍确认引擎结果进了 `data.json.active_contradictions` 且 schema 合规。

## 约定
- 动手前先 `tail` 看最新状态，避免重复/冲突。
- 只记"做了什么/对应什么功能"，绝不在笔记本写明文 token/密钥。
- 认证：本机 `set GITHUB_TOKEN=ghp_xxx` 后跑脚本；token 不进文件、不贴聊天。
- 当前 PAT 已暴露，建议尽快 revoke 换 scoped（仅 repo+过期），双方各一把独立 PAT。
