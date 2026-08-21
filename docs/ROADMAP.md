# 锌看板 · 矛盾识别框架 交接路线图 (ROADMAP)
> 维护者：CodeBuddy/YAQH侧(本机) + Hermes/腾讯云侧 双 agent
> 最后更新：2026-08-17 ｜ 读者：接手方（Hermes 或新会话）
> 配套：collab/notebook.md（实时日志）、collab/HERMES_ONBOARDING.md（机制说明）、collab/screen_zinc.py（运维）

## 0. 一句话现状
> 架构映射 / GitHub 各板块数据关联 / 权限边界矩阵 / AI 解盘产出变量穷举，详见 **docs/ARCHITECTURE.md**。
矛盾识别引擎（contradiction_engine.py）**已完整接线**进流水线：
- `fetch_zn.py:main`(1087行) 调 `run_engine` 写 `data.json.active_contradictions`（含 structured/formatted，供前端 A/B 自动重排）
- `analyze_zn.py`(711-713行) 调 `run_engine` 并把 `format_for_prompt` 注入 V2 解盘 prompt
- 引擎本身不是孤儿（此前"未接线"为搜索工具抽风误报，已在 notebook 更正）

## 1. 数据能看出矛盾吗？——能，且已分三层
| 策略 | 数据源 | 需新闻？ | 产出 |
|---|---|---|---|
| anomaly 异常波动 | 纯图表(z-score+CUSUM) | **否** | 无名异常，但带多空方向 |
| divergence 背离 | 纯图表(跨序列逻辑对) | **否** | 结构性背离(假突破/假紧张) |
| rule 规则匹配 | 新闻×9矛盾模板 | **是** | 标好"哪个矛盾活跃" |

**结论**：数据独立即可发现矛盾并判方向；新闻只负责"给矛盾贴语义标签 + 喂 LLM 叙事"。多空方向不再依赖新闻措辞——详见 §2。

## 2. 数据代理方向层（2026-08-17 新增）
**问题**：rule 策略原靠新闻里的"利多/利空"短语定方向，这类短语极少逐字出现 → 6 条全中性。
**解法**：在 `zinc_scoring.yaml` 每条矛盾加 `signal:{series, trend, direction}`，引擎 `_signal_direction()` 用底层序列趋势补方向。新闻无方向时由数据兜底，新闻有方向时作佐证。
- 配置示例：`mine_supply_tight: signal:{series: tc, trend: down, direction: 1}`（TC↓=矿紧=利多）
- 宏观/政策无单指标代理，仍靠新闻措辞。
**实测（本地快照）**：`import_window`(沪伦比↓→利空)、`galvanizing_demand`(镀锌产量↓→利空)、`lme_squeeze`(注销↑→利空) 由数据正确判出。`tc`/`smelt_profit` 快照 len=0（线上填满后即生效）；`inv_18` 实为累库(sign+1)故不触发利多信号——均属正确行为。

## 2.1 AI 解盘模型 & 为什么"改动后解盘没变"
**AI 解盘调的模型**（`analyze_zn.py`）：
- 主：`ZSUN` 端点 `zsun.funkits.cn`，模型 `Qwen36_35B`，key=`ZSUN_KEY`
- 备：`DashScope` 端点 `token-plan.cn-beijing.maas.aliyuncs.com`，模型 `qwen3.7-max`，key=`DASHSCOPE_KEY`
- **部署位置**：Hermes 的 ubuntu 服务器（`GH_STATIC_DATA="/home/ubuntu/..."`，`.env` 在他的机器）。**本机无 key、无该服务器网络，跑不了 AI 解盘**——只能本地验证 prompt 构造。

**"改了引擎但 AI 解盘没变化"的三点根因**：
1. 数据代理方向原本只注入"机器实时识别矛盾"**辅助段**(`contra_inject`)，而模型作结论主要看 prompt 里的 **18 指标数值段 + 新闻**（辅助段影响弱）→ 结论自然不变。
2. 底层 data.json（数值/新闻）没变 → 模型核心输入没变。
3. 代码 push 到 GitHub 后，**需 Hermes `git pull` + 重新跑 `analyze_zn.py`** 才在线上生效，不会自动同步。
4. "内容雷同"反而说明模型没失效——真失效会返回空/报错（`所有 AI 供应商均不可用`），不是类似文本。

**解法（已落地 2026-08-17）**：V2 模板新增 **"机器强制方向指令"段**，把 L2 引擎 high-confidence 方向（`direction≠0` 且 `confidence≥0.6`）以强指令注入，明确要求模型在【结论】【多空对比】优先采纳。本地 `build_prompt_v2` 实测注入成功（例：`异常波动·lme_canc：利空（置信1.0）`）。此改动仅改 prompt 模板，不碰 key/模型，Hermes 重跑即生效。

## 3. 9 条核心矛盾框架（zinc_scoring.yaml.contradictions，克隆自镍通用模板）
| id | 权重 | 数据代理序列(trend→方向) |
|---|---|---|
| mine_supply_tight 矿端紧缺(TC) | 5 | tc down→+1 |
| tc_rc_trend TC/RC趋势 | 5 | tc down→+1 |
| smelter_margin 冶炼利润 | 4 | smelt_profit down→-1 |
| galvanizing_demand 镀锌需求 | 4 | galvanized_prod down→-1 |
| inventory_draw 七地库存 | 5 | inv_18 down→+1 |
| import_window 进口窗口 | 3 | shfe_lme_ratio down→-1 |
| macro_liquidity 宏观 | 3 | (无，靠新闻) |
| policy_event 政策 | 3 | (无，靠新闻) |
| lme_squeeze LME挤仓 | 5 | lme_canc up→+1 |
注：`mine_supply_tight` 与 `tc_rc_trend` 同为 TC 维度，后续可合并。

## 4. 待完善清单（分工）
**CodeBuddy/YAQH侧（不依赖密钥，可本地做）**
- [x] 引擎接线确认 + 数据代理方向层 ✅(2026-08-17)
- [ ] divergence 0 命中：喂更长历史 + 校准锌配对阈值（TC↔冶炼利润、价↔库存、注销↔库存）
- [ ] 数据层镍残留过一遍：charts.js/analyze 映射 + data.json 实际字段（见 zinc_contradictions_screened.md）
- [ ] `signal` 阈值从"趋势符号"升级为"相对历史分位"(quantile_pos) 以减少噪音

**Hermes/腾讯云侧（需密钥+部署）**
- [ ] 前端消费 `active_contradictions`：charts.js 按强度自动重排/高亮（种子字段已就绪）
- [ ] 保证 `tc`/`smelt_profit` 序列在线上 data.json 有数据（当前本地快照缺失）
- [ ] 把硬编码 GUAN/DATA/NEWS_KEY 挪进 Actions Secrets
- [ ] 新闻流带情感标签，进一步提升 rule 方向精度

## 5. 低成本运维（token 极省）
```bash
python collab/screen_zinc.py --explain   # 打印 §3 九矛盾框架
python collab/screen_zinc.py             # 跑引擎出实时命中（本文件 §2 结果来源）
python collab/screen_zinc.py --regen     # 纯本地用 charts 重算写回 data.json（0 次 Zhiji）
python collab/screen_zinc.py --json      # 机读，给前端/笔记本
```
原则：每脚本单职责、只打结论不打大对象、机读给 --json、要网络显式标注成本。Hermes 服务器侧可直接复用，无需重拉 Zhiji。

## 6. 当前实时命中快照（2026-08-17 本地）
1. [anomaly] lme_canc 注销仓单异常｜强度1.0｜利空｜最新13475 环比-43.38%
2. [rule] mine_supply_tight｜1.0｜中性(tc无数据)
3. [rule] smelter_margin｜1.0｜中性(smelt_profit无数据)
4. [rule] import_window｜0.667｜**利空**(沪伦比↓)
5. [rule] galvanizing_demand｜0.333｜**利空**(镀锌产量↓)
6. [rule] inventory_draw｜0.333｜中性(七地累库)
7. [rule] policy_event｜0.333｜中性
共 7 条。
