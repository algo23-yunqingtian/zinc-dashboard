# 锌(Ni)看板 v3.0

[![Fetch Data](https://github.com/algo23-yunqingtian/zinc-dashboard/actions/workflows/fetch.yml/badge.svg)](https://github.com/algo23-yunqingtian/zinc-dashboard/actions/workflows/fetch.yml)

## 预览

- **服务器版**（推荐，实时 AI）：http://124.221.113.37:8766/zinc-gh/
- **GitHub Pages**（缓存 AI）：https://algo23-yunqingtian.github.io/zinc-dashboard/

## 功能

| 功能 | 说明 |
|---|---|
| ⚡ A核心矛盾 | LME库存、进口窗口、锌豆替代、冶炼利润 vs 库存 |
| 📊 B基本面 | 14张图表：SHFE/LME价格、持仓、沪伦比、库存、利润、产量、表观消费等 |
| 📡 实时资讯 | SMM + Mysteel 新闻，A/B/C 分级 |
| 🤖 AI解盘 | 服务器端实时调用 SiliconFlow Qwen2.5-72B，GitHub Pages 显示缓存 |
| 📐 Prompt工程 | 20套Prompt评分排名、问财vs本地AI对比 |

## 架构

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  GitHub     │     │  服务器       │     │  浏览器       │
│  Actions    │────▶│  Nginx       │────▶│  index.html   │
│  (30min)    │     │  :8766       │     │  + data.json  │
└─────────────┘     │              │     └──────────────┘
                    │  /api ──▶    │
                    │  proxy.py    │────▶ SiliconFlow
                    │  :8774       │
                    └──────────────┘
```

## 数据源

- **行情/基本面**：Zhiji API（每 30min 通过 Actions 更新）
- **新闻**：SMM + Mysteel（每 30min）
- **AI 解盘**：SiliconFlow Qwen2.5-72B（服务器端实时 / GitHub Pages 缓存）

## 本地部署

```bash
# 1. 克隆
git clone https://github.com/algo23-yunqingtian/zinc-dashboard.git
cd zinc-dashboard

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 SILICONFLOW_KEY

# 3. 启动 AI 代理
pip install requests
python proxy.py &

# 4. 配置 Nginx（见 docs/collaboration.md）
```

## 协作规则

详见 [COLLAB_RULES.md](COLLAB_RULES.md)

## License

Private
