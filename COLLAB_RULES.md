# 锌看板协作规则（v1.0 - 2026-08-10）

## 核心原则

**单一主 Agent：微信端（"哈宝"）**
- 后续所有开发、数据更新、push 都由微信端负责
- 飞书端不再主动修改代码，除非微信端明确要求

## 唯一工作目录

```
/home/ubuntu/zinc_dashboard_gh/    ← 唯一仓库
```

**其他目录已废弃**：
- `/home/ubuntu/zinc_dashboard/` — 旧版 Flask 看板，已弃用
- `/home/ubuntu/zinc_prompt_eval/` — Prompt 评估工具，数据已集成到 data.json
- `/home/ubuntu/analysis/zinc_dashboard/` — 旧 HTML，已弃用

## 文件分工（严格遵守）

### 微信端负责（唯一）
| 文件 | 职责 |
|---|---|
| `fetch_zn.py` | 数据抓取、data.json 生成 |
| `proxy_zn.py` | AI 代理（SiliconFlow） |
| `.env` | API Key（不在 git 里） |
| `.github/workflows/fetch.yml` | GitHub Actions |
| `data.json` | 唯一数据源，Actions 每 30min 更新 |
| `static/charts.js` | 前端渲染逻辑 |

### 飞书端禁止修改
- ❌ `fetch_zn.py`
- ❌ `proxy_zn.py`
- ❌ `data.json`
- ❌ `.github/workflows/`
- ❌ `static/charts.js`（除非微信端要求）

### 飞书端可以修改（需先问微信端）
- `index.html` — 页面结构
- `static/style.css` — 样式

## Git 流程

1. **微信端 push**：所有改动由微信端 commit + push
2. **飞书端不直接 push**：有改动建议时发给微信端
3. **data.json**：只有 Actions 更新，人工不 push

## 访问地址

| 版本 | 地址 | 说明 |
|---|---|---|
| 服务器版（主） | http://124.221.113.37:8766/zinc-gh/ | 实时 AI |
| GitHub Pages | https://algo23-yunqingtian.github.io/zinc-dashboard/ | 缓存 AI |

## 当前版本状态

- 5个Tab：A核心矛盾 / B基本面 / 实时资讯 / AI解盘 / Prompt工程
- 14个图表（A1-A4, B1-B14）
- AI解盘：服务器端实时，GitHub Pages 缓存
- Prompt工程：20套Prompt评分排名 + 问财vs本地对比
- 数据：Zhiji API + SMM新闻，Actions 每30min更新
