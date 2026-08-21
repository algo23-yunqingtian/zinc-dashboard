# 锌看板分析文字工程 — 交接文档 (2026-08-10)

> **上下文来源：** 飞书对话，模型 Only，上下文约 70%
> **下一步：** 新对话加载此文后，从 P0 任务开始执行

---

## 一、项目基本信息

| 项 | 值 |
|---|---|
| 仓库 | `github.com/algo23-yunqingtian/zinc-dashboard` |
| 代码路径 | `/home/ubuntu/zinc_dashboard_gh/` |
| Nginx目录 | `/home/ubuntu/zinc_gh_static/` |
| 预览地址 | `http://124.221.113.37:8766/zinc-gh/` |
| 协作规则 | **仅飞书端参与**，微信/网页/其他agent不碰 |
| Git状态 | commit `fb9bb82` 已推 origin/main |

---

## 二、当前分析文字 Pipeline（已跑通但粗糙）

```
Zhiji API ×28指标  ──► 18个chart JSON  ──► gen_analysis()规则多空
akshare 新闻×20条                       ──► gen_ai() AI解盘(只喂~8指标,300字)
                                                      ↓
                                              data.json → 前端渲染
```

**核心文件：**
- `fetch_zn.py` — 数据抓取+组装+分析生成（246行）
- `data.json` — 输出产物（~170KB）
- `static/charts.js` — 前端渲染
- `index.html` — 页面结构

---

## 三、发现的 6 个短板

| # | 短板 | 严重度 | 说明 |
|---|------|--------|------|
| ① | **AI只用了~8个指标** | 🔴 | `gen_ai()` 只取了 shfe/lme/oi/ratio/inv18/bean/profit/indo_rate；18个chart里10个没喂给AI |
| ② | **Prompt是硬编码单套** | 🔴 | 有22套老版评测+20套新版排名，但 `gen_ai()` 用的是写死的简单Prompt，评测结果没被用上 |
| ③ | **输出限制300字** | 🟡 | 深度分析300字不够，因果链被截断 |
| ④ | **规则分析阈值固定** | 🟡 | `LME<28万吨→利多` 不随市场变化 |
| ⑤ | **无人类反馈闭环** | 🔴 | 没有"人打分→Prompt自动调整"的机制 |
| ⑥ | **新闻只是罗列** | 🟡 | A/B/C分级但没被AI用来解释"为什么" |

---

## 四、优化任务拆分（P0→P3）

### P0 — 立竿见影（✅ 已完成 2026-08-10, commit 96aff18）

|| 任务 | 状态 | 说明 |
|------|------|------|
| **P0-1: 指标全覆盖** | ✅ | `gen_ai()` 新增 `gv()`/`tv()`/`fmt()` 通用辅助函数，18个chart全量提取 |
| **P0-2: 冠军Prompt** | ✅ | Top1(129分) 6步框架 + Top2(120分) 因果链融合，替换硬编码单套 |
| **P0-3: 输出扩展** | ✅ | 300字→800字，max_tokens 800→1500，5段结构化（结论→矛盾→多空→风险→建议） |

**变更统计：** fetch_zn.py 367行（+144/-33）
**验收：**
- 语法 ✓ | Git push ✓ (commit bee2cf2)
- 数据提取：4731/4731 (100%) ✓
- AI输出：800字，5段结构完整（结论→矛盾→多空→风险→建议）✓
- 输出干净（无中间过程泄漏）✓
- Nginx 同步 ✓

---

### P1 — 交叉验证

| 任务 | 内容 | 预估工时 |
|------|------|---------|
| **P1-1: 规则vsAI交叉** | gen_analysis() 多空结论 vs AI分析结论，冲突时双栏输出 | 2小时 |
| **P1-2: 新闻摘要** | LLM压缩20条新闻→3条核心新闻（事件驱动型） | 2小时 |

**验收标准：**
- data.json 新增 `cross_check` 字段（冲突标记）
- 前端显示"规则看多 vs AI看空"时高亮提醒

---

### P2 — 深度分析

| 任务 | 内容 | 预估工时 |
|------|------|---------|
| **P2-1: 多轮生成** | Round1: 识别核心矛盾(200字) → Round2: 因果推演+多空对比(800字) | 3小时 |
| **P2-2: 前端评分** | AI分析旁加评分按钮(1-10分+文字反馈)，存入DB | 半天 |

**验收标准：**
- AI分析分两段展示："核心矛盾" + "多空推演"
- 用户评分可保存，每周自动汇总

---

### P3 — 智能路由

| 任务 | 内容 | 预估工时 |
|------|------|---------|
| **P3-1: Prompt路由** | 根据数据状态自动选择Prompt策略（齐全→完整版 / 缺失→精简版 / 有重大新闻→事件驱动版） | 半天 |

---

## 五、指标选取机制（当前 vs 理想）

### 5.1 当前18个Chart的选取逻辑

| Chart | 指标(锌语义) | 属于五层框架 | 选取原因 |
|-------|------|------------|---------|
| A1_lme_inventory | LME库存/注册/注销 | 第二层-库存锚 | 锌供需核心指标 |
| A2_import_window | 沪伦比/进口盈亏/进口占比 | 第三层-价格信号 | 进口窗口开/关 |
| A3_substitution | 锌精矿TC/SHFE结算 | 第三层-替代关系 | 矿端紧缺锚(键名沿用镍版) |
| A4_smelting_pressure | 利润/18家库存/27家库存/锌锭库存 | 第二层-供给锚 | 冶炼压力综合 |
| B1_shfe_price | SHFE锌价 | 第一层-基准价 | 国内定价基准 |
| B2_lme_price | LME锌价 | 第一层-基准价 | 国际定价基准 |
| B3_shfe_oi | SHFE持仓量 | 第四层-资金情绪 | 多空博弈强度 |
| B4_ratio | 沪伦比 | 第三层-比价 | 进口窗口 |
| B5_china_inventory | 18家+27家库存 | 第二层-库存锚 | 国内库存 |
| B6_bean_inventory | 锌锭库存 | 第二层-供给锚 | 社会库存 |
| B7_smelting_profit | 冶炼利润 | 第二层-供给锚 | 冶炼瓶颈 |
| B8_china_production | 中国产量/产能 | 第二层-供给锚 | 国内供给 |
| B9_indonesia | 镀锌板产量/产能/开工率 | 第二层-供给锚 | 最大下游(~70%消费,键名沿用镍版) |
| B10_sulfate_price | 硫酸锌价格(占位,数据点稀疏) | 第二层-需求锚 | 氧化锌/化工需求 |
| B11_lme_flow | LME流入/流出 | 第二层-库存锚 | 隐性库存流动 |
| B12_apparent_consumption | 表观消费 | 第二层-需求锚 | 总需求代理 |
| B13_lme_funding | 资金面(4维度) | 第四层-资金情绪 | 新增，LME融资 |
| B14_stainless | 广东0#锌锭升贴水 | 第三层-价差信号 | 现货强弱(键名沿用镍版) |

> ⚠️ 注：A3/B9/B14 等 chart 键名沿用镍版结构（A3_substitution / B9_indonesia / B14_stainless），
> 但其承载的已是锌数据。完整键名→锌语义映射见 `docs/zinc_frame.md` 第3节。

**覆盖度评估：**
- 第一层（产业链）：✅ B1/B2 基准价
- 第二层（供需库存）：✅ A1/A2/A3/A4/B4/B5/B6/B7/B8/B9/B10/B11/B12/B14 — **覆盖最全面**
- 第三层（价格信号）：✅ A2/A3/B4
- 第四层（资金情绪）：⚠️ B3/B13 — **偏弱**
- 第五层（事件政策）：❌ **缺失**，只有新闻列表没有政策日历

**优化建议：**
1. 补充 CFTC 持仓（第四层）
2. 补充期限结构 Contango/Backwardation（第三层）
3. 补充硫酸锌产量（第二层-需求锚，新能源电池~15%）

### 5.2 通用化指标选取机制（待实现）

```
目标：给定任何品种名，自动输出 Top N 核心指标 + 打分

流程：
Step 1: 品种名 → 调用 commodity-core-indicator-extraction Skill
        → 快速锁定 Top 3-5 核心指标

Step 2: 调用 commodity-indicator-screening Skill
        → 五层框架 + 打分卡 → 输出 15-20 个入选指标

Step 3: 验证数据可得性
        → 检查 Zhiji API / akshare / 本地DB 是否有数据
        → 无数据的标记为"待接入"

Step 4: 生成品种配置 JSON
        → 写入 [品种]_config.json（含指标ID映射+数据源）
        → fetch_zn.py 读取配置，自动抓取

Step 5: 回测验证（可选）
        → 历史数据跑相关性 → 确认领先性
```

**产物：**
- 通用 Skill（已创建）：`commodity-indicator-screening` + `commodity-core-indicator-extraction`
- 待创建：`generate_chart_config.py`（品种名→配置JSON的自动化脚本）
- 待创建：`validate_leadership.py`（回测领先性验证）

---

## 六、Prompt 训练与迭代机制

### 6.1 当前状态
- 22 套老版 Prompt 评测数据（在 `old_prompt_data` 中）
- 20 套新版 Prompt 排名（在 `prompt_data.rankings` 中）
- **但 `gen_ai()` 用的是写死的简单Prompt，评测结果没被用上**

### 6.2 冠军 Prompt 生成流程（待实现）

```
Step 1: 从 prompt_data.rankings 取 Top 3
Step 2: 人工融合：
        - Top1 的结构框架
        - Top2 的因果链格式
        - Top3 的风险提示要求
Step 3: 去掉重复指令，加入"禁止事项"
Step 4: 写入 fetch_zn.py 的 gen_ai() 作为默认 Prompt
Step 5: 后续每次 gen_ai() 运行后，自动打分 → 累计 → 月度更新
```

### 6.3 持续迭代闭环

```
gen_ai() 生成分析
       ↓
用户在前端评分 (1-10分 + 文字反馈)
       ↓
反馈存入 SQLite/JSON
       ↓
每周汇总：平均分 < 7 → 触发 Prompt 调整
       ↓
调整策略：
  - 如果"因果链不完整" → 加强因果指令
  - 如果"数据使用率低" → 减少指标数量
  - 如果"结论模糊" → 强制要求"看多/看空/中性"
       ↓
更新冠军 Prompt → 下一轮 gen_ai() 使用
```

### 6.4 跨 Agent 复用条件

| 条件 | 要求 |
|------|------|
| 模型能力 | GPT-4 / Claude / Gemini 级别（因果推理能力） |
| 数据源 | 能读取 Zhiji API 或等价数据源 |
| 输入格式 | JSON Schema 规范（已定义） |
| 输出格式 | Markdown 结构规范（待定义） |

---

## 七、关键技术参数

| 项 | 值 |
|---|---|
| Zhiji API key | `~/.hermes/scripts/zhiji_api.py` 第15行 |
| SiliconFlow key | `/home/ubuntu/zinc_dashboard_gh/.env` 中 `SILICONFLOW_KEY` |
| SiliconFlow 模型 | `SF_MODEL` (fetch_zn.py 中定义) |
| 数据抓取命令 | `ZHJI_KEY=<key> SILICONFLOW_KEY=$(grep SILICONFLOW_KEY .env\|cut -d= -f2) python3 fetch_zn.py` |
| 同步到Nginx | `cp data.json index.html /home/ubuntu/zinc_gh_static/ && cp -r static/* /home/ubuntu/zinc_gh_static/static/` |

---

## 八、待创建的 Skill / 脚本

| 名称 | 类型 | 说明 |
|------|------|------|
| `generate_chart_config.py` | 脚本 | 品种名 → 配置JSON（指标ID映射） |
| `validate_leadership.py` | 脚本 | 回测指标领先性 |
| `prompt_trainer.py` | 脚本 | 从评测数据自动合成冠军Prompt |
| `ai_analysis_scoring.py` | 脚本 | AI输出自动6维度打分 |
| `prompt-engineering-pipeline` | Skill | Prompt迭代闭环的标准化流程 |

---

## 九、本轮对话已完成的 Skill

| Skill | 路径 | 说明 |
|-------|------|------|
| `commodity-indicator-screening` | `commodity-research/` | 五层筛选框架+打分卡 |
| `commodity-core-indicator-extraction` | `commodity-research/` | 3分钟快速提炼Top3-5核心指标 |

---

## 十、进度与下一步

### 已完成
- [x] **P0** (commit 858895d): 指标全覆盖 + 冠军Prompt + 结构化输出
- [x] **P1** (commit 8b160bd): 规则vsAI交叉验证 + 新闻A/B分级摘要 + AI核心资讯
- [x] **P2** (commit 12a8210): 思维链Prompt + 前端评分组件
- [x] **P3** (commit 9eabe20): AI失败回退规则分析 + 前端规则面板 + 交叉检查指示器

### 下一步
1. **用户验收 P0** → 运行 `fetch_zn.py` 产��实际 AI 分析，反馈打分
2. **进入 P1** → 规则vsAI交叉验证 + 新闻摘要LLM压缩
3. **进入 P2** → 多轮生成 + 前端评分
4. **进入 P3** → Prompt智能路由

---

*文档版本: v2 | 更新时间: 2026-08-10 | 下次更新: P0验收后*
