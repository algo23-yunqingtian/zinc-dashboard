# 锌看板协作规范 (COLLAB_RULES — 现实对齐版 v2)

> 更新于 2026-08-17。本文取代旧版（旧版误把镍看板的"微信端/飞书端 Hermes"分工和 `fetch_data.py`/`proxy.py` 文件名照搬进来，与锌看板实际不符）。

## 0. 协作模型（现实）
- **两个 agent，一个真相源**：GitHub 仓库 `algo23-yunqingtian/zinc-dashboard` 的 `main` 分支 = 唯一 source of truth。本地永远是副本。
- **CodeBuddy（YAQH 侧 / 本机 Windows）**：无 git CLI，全部走 GitHub Contents API（`collab/push.py` / `collab/log.py`）。负责：指标层理论、矛盾引擎逻辑、文档/协作机制、按用户授权可 push。
- **Hermes（腾讯云 / 原"微信端"）**：有 git + 服务器（`/home/ubuntu/zinc_dashboard_gh/`），持有 Zhiji/腾讯云 DB/akshare 与 AI 密钥。负责：真实数据拉取、部署、AI 解盘、前端 `charts.js`。
- **双方都可用 PAT push**（2026-08-17 用户授权，打破旧版"仅微信端 push"）。

## 1. 沟通总线（后台，不在看板 UI）
- `collab/notebook.md`：共享笔记本，每次增删改追加一条（时间/agent/动作/目标/功能说明/沟通）。
- `collab/log.py`：读写助手（`add`/`tail`，含并发冲突重试）。Windows 侧中文用 `--desc-file/--note-file`。
- `collab/push.py`：无 git 推送助手（读 `GITHUB_TOKEN` 环境变量）。
- `collab/verify_active_contradictions.py`：离线探针，检测"自动矛盾识别"是否真的接通 + 实跑引擎（见 §4）。

## 2. 真实文件结构
| 文件 | 作用 | 归属层 |
|---|---|---|
| `fetch_zn.py` | 抓数 + 新闻 + 流水线 main | 数据接入 |
| `indicator_lib.py` | 指标层 L1：`SERIES_REGISTRY` + 方向/波动率/zscore/cusum | 指标层 |
| `contradiction_engine.py` | 矛盾引擎 L2：rule/anomaly/divergence 三策略 + 去重 | 矛盾识别 |
| `scorer_v2_zn.py` | 新闻评分 L3：噪音过滤 + 多空打分 + 相关性闸门 | 矛盾识别 |
| `zinc_scoring.yaml` | 矛盾/指标/关键词配置（**克隆自 `nickel_scoring.yaml` 通用模板**） | 配置 |
| `analyze_zn.py` + `analyze.py` | AI 解盘 prompt 链 | 产出 |
| `charts.js` | 前端展示 / 自动重排 | 前端 |
| `fetch.yml` | Actions 调度（每 30 分钟） | 部署 |

## 3. 框架来源（重要：锌确实参考了镍/通用框架）
- `zinc_scoring.yaml` 注释 `version: 2.0.0 = 首次从镍框架复刻为锌框架`，结构（core_indicators→contradictions→relevance→tiers→negative_filters→scoring→ranking）与 `nickel_scoring.yaml` **完全一致**，按锌产业链重命名。
- `docs/zinc_frame.md` 克隆自镍的 `docs/analysis_frame.md`（镍仓库已 404，但结构已继承）。
- 即：**"通用有色金属模板" = 镍的 scoring 结构**，锌是第二个应用者。镍的特征值（印尼 NPI/不锈钢）已替换为锌的特征值（矿端 TC/冶炼利润/镀锌/LME 挤仓）。

## 4. 当前已知缺口（Hermes 接手重点）
1. **矛盾引擎未接线**：`fetch_zn.py:main` 未调用 `run_engine` 写 `active_contradictions`；`analyze_zn.py` 未注入 `format_for_prompt` 文本（`collab/verify_active_contradictions.py` 实测：`active_contradictions=False`，但引擎在真实 charts 上能识别 `anomaly_lme_canc`）。→ 接好这两处，自动矛盾识别即生效。
2. **rule/divergence 策略数据不足**：当前 `data.json` 序列历史偏短，`prefilter` 丢弃短序列导致仅 1 条 anomaly 命中。需保留更长历史 / 调阈值让规则类矛盾也触发。
3. **数据层镍残留**：`zinc_contradictions_screened.md` 记录的 `B9_indonesia`/`B14_stainless`/`A2.indonesia_npi_rate` 在 `indicator_lib` 的 SERIES_REGISTRY 已清为 `B9_galvanizing`/`B14_premium`，但 `data.json` 实际字段与 `charts.js`/`analyze_zn.py` 映射需全量核对一次。
4. **密钥硬编码**：`GUAN_KEY/DATA_KEY/NEWS_KEY` 写死在 public 仓库，建议挪进 GitHub Actions Secrets / `.env`。

## 5. 红线
- **zhiji 新闻 API 严格限流**：勿频繁手动拉；生产保持 `fetch.yml` 每 30 分钟一次。`fetch_news` 一次内调 6 次 zhiji，触限流降频/减关键词。
- token / 密钥绝不写进 `collab/notebook.md` 或任何仓库文件。
