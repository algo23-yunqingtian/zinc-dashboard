# Nickel Dashboard — 协作规范

## 仓库信息

- **URL**: https://github.com/algo23-yunqingtian/zinc-dashboard
- **GitHub Pages**: https://algo23-yunqingtian.github.io/zinc-dashboard/
- **服务器版（推荐）**: http://124.221.113.37:8766/zinc-gh/
- **默认分支**: `main`

## 两个 Agent 分工

| 角色 | 负责文件 | 不碰的文件 |
|------|----------|-----------|
| **微信端 Hermes** | `fetch_data.py`, `proxy.py`, `requirements.txt`, `.github/workflows/fetch.yml`, Nginx/Supervisor 配置 | `index.html`, `static/` (charts.js, style.css) |
| **飞书端 Hermes** | `index.html`, `static/charts.js`, `static/style.css`, UI 逻辑 | `data.json`, `fetch_data.py`, `proxy.py`, workflow |

## 架构

```
┌──────────────────────────────────────────────────────────────┐
│  用户浏览器                                                    │
│  http://124.221.113.37:8766/zinc-gh/                      │
│  (Nginx 8766 反向代理)                                         │
└──────────┬───────────────────────────────────────┬────────────┘
           │                                       │
    ┌──────▼────────┐                    ┌────────▼────────┐
    │  静态文件托管    │                    │  AI Proxy (8774)  │
    │  zinc_gh_   │                    │  proxy.py        │
    │  static/       │                    │  (Supervisor)    │
    │  index.html    │                    │                  │
    │  data.json     │                    └────────┬─────────┘
    │  static/*      │                             │
    └────────────────┘                    ┌────────▼────────┐
                                          │  SiliconFlow API   │
                                          │  Qwen2.5-72B       │
                                          └───────────────────┘

GitHub Actions (每30min)
    └─> 更新 data.json → git push → GitHub Pages + 同步到服务器
```

## AI 实时解盘流程

1. 用户打开看板 → `data.json` 加载，**先显示缓存的 AI 解盘**
2. 前端 JS 从 `data.json` 提取最新数据 → POST 到 `/zinc-gh/api`
3. Nginx 转发到 `proxy.py` (8774) → 转发到 SiliconFlow
4. 结果返回前端 → **替换缓存，显示"🟢 实时"时间戳**
5. 如果调用失败 → 回退到缓存数据，显示"⚠️ 使用缓存"

## 协作规则

### 日常开发
- 各自改各自的文件 → commit → push 到 `main`
- 因为文件隔离，极少冲突
- 如果冲突（同时改同一个 workflow），后推的人先 pull rebase 再 push

### 大改动
1. 开 feature branch: `git checkout -b feature/xxx`
2. 开发完成后 push branch
3. 创建 PR: `gh pr create --base main --head feature/xxx --title "描述" --body "改了什么"`
4. 另一方 review 后 merge

### 变更日志
每次改动在 `docs/change_log.md` 加一行：
```
[YYYY-MM-DD HH:MM] [微信/飞书] 简述改动
```

### 部署同步
微信端 Agent 负责把 GitHub 上的文件同步到 `/home/ubuntu/zinc_gh_static/`：
```bash
cp /home/ubuntu/zinc_dashboard_gh/index.html /home/ubuntu/zinc_gh_static/
cp /home/ubuntu/zinc_dashboard_gh/static/* /home/ubuntu/zinc_gh_static/static/
cp /home/ubuntu/zinc_dashboard_gh/data.json /home/ubuntu/zinc_gh_static/
```

### 数据管道
- GitHub Actions 每 30 分钟自动运行 `fetch.yml`
- 需要改 API key 时更新 GitHub Secrets（Settings → Secrets）
- Secrets: `ZHJI_KEY`, `SILICONFLOW_KEY`

### 紧急修复
- 直接在 `main` 上改 → commit → push → 同步到服务器
- 事后在 change_log 补记录

## 文件说明

| 文件 | 用途 |
|------|------|
| `index.html` | 主看板页面 |
| `static/charts.js` | 图表逻辑 + AI 实时调用 |
| `static/style.css` | 样式 |
| `data.json` | 数据源（Actions 更新） |
| `fetch_data.py` | 数据抓取脚本 |
| `proxy.py` | AI 代理（浏览器 → SiliconFlow） |
| `.github/workflows/fetch.yml` | 定时数据更新（每 30min） |
| `.env` | 环境变量（Key，不计入 Git） |
| `docs/collaboration.md` | 本文件 |
| `docs/change_log.md` | 变更记录 |

## 本地开发

```bash
# Clone
git clone https://github.com/algo23-yunqingtian/zinc-dashboard.git

# Push
git add -A && git commit -m "描述" && git push origin main
```
