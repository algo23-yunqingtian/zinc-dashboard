#!/usr/bin/env python3
"""
zinc real-time AI analyzer module.
Reads data.json + fetches news -> builds prompt -> calls AI -> returns analysis.
"""
import json, os, re, sys, sqlite3, urllib.request, urllib.parse, socket
from datetime import datetime

# 统一新闻打分模块 (scorer v2 + 相关性闸门)
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scorer_v2_zn as scorer_v2

# L1 指标标准化 + L2 矛盾识别引擎（L4 投喂接入）
from indicator_lib import prefilter
from contradiction_engine import run_engine, format_for_prompt

# Force IPv4 — dashscope IPv6 endpoint times out
_original_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    results = _original_getaddrinfo(*args, **kwargs)
    return [r for r in results if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only_getaddrinfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(BASE_DIR, "data.json")
GH_STATIC_DATA = "/home/ubuntu/zinc_gh_static/data.json"
ZINC_DB = "/home/ubuntu/analysis/zinc_v1.db"

DASHSCOPE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODEL = "qwen3.7-max"

ZSUN_URL = "https://zsun.funkits.cn/v1/chat/completions"
ZSUN_MODEL = "Qwen36_35B"

# 模型优先级：zsun 为主（稳定），DashScope 为备用
AI_MODEL_ORDER = ["zsun", "dashscope"]

def load_data():
    # Priority: gh_static (synced from GH Actions, has real data) > local data.json
    for path in [GH_STATIC_DATA, DATA_JSON]:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return None

# ── News filtering ──
# 低优先级噪音：收盘/开盘/报价/技术面总结（基本面无价值）
_EXCLUDE_NOISE = ['SHFE夜盘收盘','LME夜盘收盘','SHFE最新','LME库存','LME注销仓单',
    'LME现货结算','SHFE.*仓单','上期所基本金属仓单','LME金属技术策略',
    'SHFE夜盘开盘','SHFE开盘_基本','SHFE收盘_基本','本周均价','锌现货报价',
    '金川集团电解锌出厂','锌钴中间品价格',
    # 盘后走势总结/技术面分析（与基本面关系极小）
    '收盘总结','走势总结','盘后总结','日度回顾','周度回顾','月度回顾',
    '技术面','技术形态','均线','MACD','KDJ','RSI','布林','金叉','死叉',
    '支撑位','压力位','突破','回落','反弹','震荡整理','多空博弈']
# 高权重关键词（锌产业链核心事件：矿端/冶炼/政策）
_HIGH_WEIGHT_KW = ['锌精矿','锌矿','加工费','TC','冶炼','减产','停产','事故','罢工',
    '限产','检修','环保督查','制裁','关税','出口限制','进口盈亏']
# 重要基本面关键词
_BASIC_KW = ['LME','库存','产量','检修','关税','镀锌','排产',
    '冶炼','精炼','锌矿','锌锭','锌合金','氧化锌',
    '表观消费','进出口','进口盈亏','仓单','注册','注销',
    '房地产','基建','汽车','家电','基金持仓','持仓','多头','空头',
    '期现','基差','进口','沪锌','伦锌']
def fetch_news():
    """Get recent zinc-related news — 统一 scorer v2 打分 (与 fetch_data.py 同一标准)
    结构: title/body/source/time/level/score/url/direction/relevant/contradictions/matched_terms"""
    items = []

    # 0. 优先从 Zhiji 讯服务拉取（最新、最全、实时）
    NEWS_BASE = "https://zhiji-ai.xyz/news/api"
    env_keys = _load_env_keys()
    news_key = env_keys.get("NEWS_KEY", "")
    if news_key:
        try:
            import urllib.request as _ur
            url = f"{NEWS_BASE}/search?q={urllib.parse.quote('锌')}&hours=48&limit=30&source=all"
            req = _ur.Request(url, headers={"X-News-Key": news_key, "User-Agent": "Mozilla/5.0"})
            with _ur.urlopen(req, timeout=10) as resp:
                zhiji_news = json.loads(resp.read())
            if zhiji_news and isinstance(zhiji_news, dict) and "items" in zhiji_news:
                source_map = {"jin10":"金十","cls":"财联社","sina":"新浪","smm":"上海有色网","x":"X"}
                for n in zhiji_news["items"]:
                    content = n.get("content", "")
                    if scorer_v2.is_noise(content):
                        continue
                    title = n.get("title", "")[:80]
                    if not title:
                        continue
                    src_name = source_map.get(n.get("source","all"), n.get("source",""))
                    items.append(scorer_v2.build_entry(
                        title, content, src_name,
                        n.get("time",""), n.get("url","")))
                print(f"  [analyze] Zhiji news: {len(items)} items")
        except Exception as e:
            print(f"  [analyze] Zhiji news failed: {e}")

    # 1. 本地DB补充（SMM日报缓存，作为 fallback）
    if len(items) < 10:
        try:
            conn = sqlite3.connect(ZINC_DB)
            c = conn.cursor()
            c.execute("SELECT date, content, source FROM news_zinc_scored WHERE date >= date('now', '-7 days') ORDER BY date DESC LIMIT 20")
            for row in c.fetchall():
                ts, content, source = row
                m = re.search(r'【([^】]+)】', content)
                if m:
                    title, body = m.group(1), content[m.end():].strip()[:200]
                else:
                    title, body = content[:60], content[60:].strip()[:200]
                title = title.replace('SHMET','').replace('上海金属网','').strip()
                if not title or title == '快讯':
                    continue
                if scorer_v2.is_noise(content):
                    continue
                # 去重：如果 Zhiji 已有相似标题则跳过（用 Jaccard 相似度）
                def _similar(t1, t2):
                    s1 = set(t1)
                    s2 = set(t2)
                    if not s2:
                        return False
                    return len(s1 & s2) / len(s1 | s2) > 0.6
                if not any(_similar(title, x["title"]) for x in items):
                    items.append(scorer_v2.build_entry(
                        title[:80], content, source or "SMM",
                        ts[:19] if ts else ""))
            conn.close()
        except Exception as e:
            if not items:
                items = [{"title":"新闻获取失败","body":str(e)[:100],"source":"系统","time":datetime.now().strftime("%Y-%m-%d %H:%M"),"level":"C","score":0,"relevant":True}]

    # 统一排序: 相关度 → 分数 → 时间 (与 fetch_data.py 同标准, 高分新闻优先进 Prompt)
    items.sort(key=lambda x: (x.get("relevant", True), x.get("score", 0), x.get("time", "")), reverse=True)
    return items[:20]

def fetch_reports():
    """研报/策略观点 — Zhiji 讯服务(实时) + 本地DB(fallback)"""
    reports = []

    # 0. 优先从 Zhiji 讯服务拉取研报类资讯
    try:
        NEWS_BASE = "https://zhiji-ai.xyz/news/api"
        env_keys = _load_env_keys()
        news_key = env_keys.get("NEWS_KEY", "")
        if news_key:
            import urllib.request as _ur
            for q in ["锌 策略", "锌 研报", "精炼锌 展望", "锌期货 分析"]:
                if len(reports) >= 5:
                    break
                url = f"{NEWS_BASE}/search?q={urllib.parse.quote(q)}&hours=168&limit=8&source=all"
                req = _ur.Request(url, headers={"X-News-Key": news_key, "User-Agent": "Mozilla/5.0"})
                with _ur.urlopen(req, timeout=8) as resp:
                    zhiji_res = json.loads(resp.read())
                if zhiji_res and isinstance(zhiji_res, dict) and "items" in zhiji_res:
                    seen = {r["title"] for r in reports}
                    for n in zhiji_res["items"]:
                        title = n.get("title", "")[:80]
                        if not title or title in seen:
                            continue
                        content = n.get("content", "")
                        if not any(k in content for k in ['策略','研报','推荐','看好','看空','目标价','展望','趋势','建议','多空','方向']):
                            continue
                        reports.append({
                            "title": title,
                            "body": content[:200],
                            "time": n.get("time", "")[:19],
                            "source": "研报"
                        })
                        seen.add(title)
            print(f"  [analyze] Zhiji reports: {len(reports)} items")
    except Exception as e:
        print(f"  [analyze] Zhiji reports failed: {e}")

    # 1. 本地DB补充（SMM高分新闻作为 fallback）
    if len(reports) < 5:
        try:
            conn = sqlite3.connect(ZINC_DB)
            c = conn.cursor()
            c.execute("SELECT date, content FROM news_zinc_scored WHERE score >= 8 ORDER BY score DESC LIMIT 5")
            for row in c.fetchall():
                ts, content = row
                m = re.search(r'【([^】]+)】', content)
                if m:
                    title = m.group(1).replace('SHMET','').replace('上海金属网','').strip()
                    body = content[m.end():].strip()[:200]
                    if any(k in content for k in ['策略','研报','推荐','看好','看空','目标价']):
                        if title not in {r["title"] for r in reports}:
                            reports.append({"title":title,"body":body,"time":ts[:19],"source":"DB"})
            conn.close()
        except Exception:
            pass

    return reports[:5]

# ── Data extraction helpers ──
def last_val(pts):
    if isinstance(pts, list) and pts:
        for p in reversed(pts):
            if p.get("value") is not None:
                return round(p["value"], 2)
    return None

def gv(chart_key, sub_key=None, charts=None):
    if charts is None:
        return (None, [])
    c = charts.get(chart_key, [])
    if sub_key and isinstance(c, dict):
        pts = c.get(sub_key, []) or []  # Handle null JSON values
    else:
        pts = c if isinstance(c, list) else []
    recent = [p["value"] for p in pts[-5:] if p.get("value") is not None][-5:]
    lv = recent[-1] if recent else None
    return (lv, recent)

def fmt(v, unit="", suffix=""):
    if v is not None:
        return f"{v:,.0f}{unit}{suffix}"
    return "N/A"

def trend_str(t):
    if len(t) >= 3:
        d = t[-1] - t[0]
        return f"{'↑' if d>0 else '↓'}{abs(d):,.0f}"
    return "—"

# ── Build prompt from data ──
def build_prompt(charts, news, reports):
    # 新闻新鲜度标注：计算每条新闻距今多少小时
    def _age_hours(time_str):
        if not time_str:
            return "?"
        try:
            # 支持 "2026-08-15 14:30:00" 或 "2026-08-15T14:30:00"
            ts = time_str.replace("T", " ")[:16]
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
            diff = (datetime.now() - dt).total_seconds() / 3600
            return f"{diff:.0f}h" if diff < 24 else f"{diff/24:.1f}d"
        except Exception:
            return "?"

    def _dir_tag(n):
        d = n.get("direction")
        return "利多" if d == "bullish" else ("利空" if d == "bearish" else "")
    nl = "\n".join(f"[{n.get('level','C')}|{n.get('score',0)}分|{_dir_tag(n)}] {n.get('title','')} ({n.get('source','')} | {n.get('time','')} | 距今{_age_hours(n.get('time',''))})" for n in (news or [])[:15])
    rp = "\n".join(f"[研报] {r.get('title','')}: {r.get('body','')[:100]} ({r.get('time','')})" for r in (reports or [])[:8])

    # 提取18个指标（槽位名沿用镍版结构, 语义=锌产业链）
    a1_inv, a1_inv_t = gv("A1_lme_inventory", "inventory", charts)
    a1_reg, _ = gv("A1_lme_inventory", "registered", charts)
    a1_canc, _ = gv("A1_lme_inventory", "cancelled", charts)
    a2_ratio, a2_ratio_t = gv("A2_import_window", "shfe_lme_ratio", charts)
    a2_magma, _ = gv("A2_import_window", "magma_discount", charts)        # 进口盈亏(元/吨, 不含税)
    a2_npi, _ = gv("A2_import_window", "import_ratio", charts)      # 进口占比(%)
    a3_bean, _ = gv("A3_substitution", "zinc_bean", charts)               # 进口锌精矿TC(美元/干吨)
    a3_shfe, _ = gv("A3_substitution", "shfe_settle", charts)
    a4_profit, a4_profit_t = gv("A4_smelting_pressure", "profit", charts)  # 进口盈亏(含税)
    a4_inv18, _ = gv("A4_smelting_pressure", "inv_18", charts)
    a4_inv27, _ = gv("A4_smelting_pressure", "inv_27", charts)
    a4_bean, _ = gv("A4_smelting_pressure", "bean_inv", charts)
    b1, b1_t = gv("B1_shfe_price", charts=charts)
    b2, b2_t = gv("B2_lme_price", charts=charts)
    b3, b3_t = gv("B3_shfe_oi", charts=charts)
    b4, b4_t = gv("B4_ratio", charts=charts)
    b5_18, b5_18_t = gv("B5_china_inventory", "inv_18", charts)
    b5_27, b5_27_t = gv("B5_china_inventory", "inv_27", charts)
    b6, b6_t = gv("B6_zinc_concentrate_tc", charts=charts)
    b7, b7_t = gv("B7_smelting_profit", charts=charts)
    b8_prod, _ = gv("B8_china_production", "chinese_prod", charts)
    b8_cap, _ = gv("B8_china_production", "chinese_cap", charts)
    b9_prod, _ = gv("B9_galvanizing", "galvanized_prod", charts)
    b9_cap, _ = gv("B9_galvanizing", "apparent_cons", charts)
    b9_rate, b9_rate_t = gv("B9_galvanizing", "alloy_rate", charts)
    b10, b10_t = gv("B10_sulfate_price", charts=charts)
    b11_out, _ = gv("B11_lme_flow", "outflow", charts)
    b11_in, _ = gv("B11_lme_flow", "inflow", charts)
    b12, b12_t = gv("B12_apparent_consumption", charts=charts)
    b13_pos, _ = gv("B13_lme_funding", "position", charts)
    b13_fl, _ = gv("B13_lme_funding", "fund_long", charts)
    b13_cl, _ = gv("B13_lme_funding", "comm_long", charts)
    b13_cs, _ = gv("B13_lme_funding", "comm_short", charts)
    b14_cr, b14_cr_t = gv("B14_premium", "guangdong_premium", charts)

    # ── 动态权重调整 ──
    def _volatility(vals):
        """近5日波动率"""
        if len(vals) < 3:
            return 0
        avg = sum(vals) / len(vals)
        if avg == 0:
            return 0
        return (sum((v - avg) ** 2 for v in vals) / len(vals)) ** 0.5 / abs(avg)

    supply_vol = _volatility(b7_t) + _volatility(b9_rate_t)
    inventory_vol = _volatility(a1_inv_t) + _volatility(b5_18_t)
    demand_vol = _volatility(b12_t) + _volatility(b14_cr_t)
    capital_vol = _volatility(b3_t) if b3_t else 0

    max_vol = max(supply_vol, inventory_vol, demand_vol, capital_vol, 0.001)
    w_supply = max(20, min(45, int(35 + (supply_vol / max_vol - 0.5) * 15)))
    w_inventory = max(15, min(35, int(25 + (inventory_vol / max_vol - 0.5) * 15)))
    w_demand = max(10, min(30, int(20 + (demand_vol / max_vol - 0.5) * 10)))
    w_capital = max(5, min(25, int(15 + (capital_vol / max_vol - 0.5) * 15)))
    w_info = max(5, 100 - w_supply - w_inventory - w_demand - w_capital)

    weight_note = f"当前动态权重：供给{w_supply}% | 库存{w_inventory}% | 需求{w_demand}% | 资金{w_capital}% | 资讯{w_info}%"

    prompt = f"""你是一位专业的锌(Zn)期货分析师。请根据以下数据，按【6步框架】给出实时解盘。

## 一、输入数据（18个Chart）

### 基准价格
- 沪锌SHFE结算价: {fmt(b1,"元/吨")}（近5日:{b1_t}，变化:{trend_str(b1_t)}）
- LME锌现货结算价: {fmt(b2,"美元/吨")}（近5日:{b2_t}，变化:{trend_str(b2_t)}）
- 沪伦比: {fmt(b4,"")}（近5日:{b4_t}，<0.96进口窗口打开）
- 进口锌精矿TC: {fmt(a3_bean,"美元/干吨")}（矿端核心指标，负值=冶炼亏损） / 沪锌结算: {fmt(a3_shfe,"元/吨")}

### LME库存与仓单
- LME总库存: {fmt(a1_inv,"吨")}（变化:{trend_str(a1_inv_t)}）
- 注册仓单: {fmt(a1_reg,"吨")} | 注销仓单: {fmt(a1_canc,"吨")}

### 国内库存
- 国内8省锌锭库存: {fmt(b5_18,"万吨")}（变化:{trend_str(b5_18_t)}）
- 锌锭现货库存(中国日度): {fmt(b5_27,"万吨")}（变化:{trend_str(b5_27_t)}）

### 矿端与冶炼供给
- 进口锌精矿TC: {fmt(b6,"美元/干吨")}（变化:{trend_str(b6_t)}，下行=矿紧=利多）
- 精炼锌月产量: {fmt(b8_prod,"万吨/月")} | 产能利用率: {fmt(b8_cap,"%")}
- 锌合金开工率: {fmt(b9_rate,"%")}（变化:{trend_str(b9_rate_t)}）

### 进口窗口
- 锌锭进口盈亏(不含税): {fmt(a2_magma,"元/吨")}（负值=进口窗口关闭）
- 进口占比: {fmt(a2_npi,"%")} | 含税进口盈亏: {fmt(a4_profit,"元/吨")}

### 需求侧
- 镀锌板周产量: {fmt(b9_prod,"万吨")}（占锌消费60%+，需求核心指标）
- 表观消费: {fmt(b12,"万吨/月")}（变化:{trend_str(b12_t)}）
- 广东0#锌锭升贴水: {fmt(b14_cr,"元/吨")}（变化:{trend_str(b14_cr_t)}，升水走扩=需求回暖）

### 资金面
- SHFE持仓: {fmt(b3,"手")}（变化:{trend_str(b3_t)}）
- LME持仓: {fmt(b13_pos,"手")} | 基金多头: {fmt(b13_fl,"手")}
- 商业多头: {fmt(b13_cl,"手")} | 商业空头: {fmt(b13_cs,"手")}

### 产业资讯
{nl}

### 研报观点
{rp if rp else "暂无研报观点"}

## 二、分析流程（思维链·内部完成）

### 第1步：信号分类
将上方18个指标逐一归类为利多或利空信号，标注强弱（强/中/弱）。

### 第2步：权重打分
{weight_note}
→ 计算多空加权总分，得出方向判断。

### 第3步：核心矛盾识别
找出当前权重最高且边际变化最大的1-2个矛盾点。

### 第4步：因果推演
从核心矛盾出发，推导价格传导链条（指标→供需→价格→资金反应）。

### 第5步：交叉验证
用其他指标验证核心矛盾方向是否一致，标记冲突信号。

**以上步骤在内部完成，不输出中间过程。**

## 三、最终输出（结构化研报，面向客户）

**【结论】**偏多/偏空/中性（一句话概括行情阶段+核心矛盾，20字以内）

**【核心矛盾】**当前最核心的供需矛盾是什么，用数据支撑（1-2条，每条50字以内）

**【多空对比】**
- 利多：信号1（强度·验证状态）；信号2（强度·验证状态）
- 利空：信号1（强度·验证状态）；信号2（强度·验证状态）

**【风险】**3-5条具体证伪路径（"若X发生→Y逻辑被证伪→价格方向"，每条40字以内）

**【建议】**方向 + 关键价位（支撑/阻力） + 确认条件 + 止损触发

**【资讯与研报】**从上方产业资讯和研报观点中提炼3-5条最核心的信息，每条格式：`[事件/观点] → [影响方向] → [对锌价影响]`，控制在3句话以内。

## 四、硬约束
1. 所有数据必须来自输入，禁止编造
2. 明确给出"偏多/偏空/中性"判断，禁止模棱两可
3. N/A的数据标注"缺失"，不要推测
4. 每条风险必须有具体触发条件
5. 结论与多空信号方向必须一致
6. 输出控制在800字以内"""
    return prompt

# ════════════════════════════════════════════════════════════
# Prompt 版本管理（V1 原版保留 + V2 试点改版，可多轮对比）
# 版本切换: 环境变量 PROMPT_VERSION=v1|v2 （默认 v2）
# ════════════════════════════════════════════════════════════
def get_active_prompt_version():
    v = os.environ.get("PROMPT_VERSION", "v2").strip().lower()
    return v if v in ("v1", "v2") else "v2"

def build_prompt_active(charts, news, reports, macro=None, version=None):
    v = version or get_active_prompt_version()
    if v == "v1":
        return build_prompt(charts, news, reports)
    return build_prompt_v2(charts, news, reports, macro=macro)

# ── V2 数据段提取 ──
def _pct_20d(pts):
    """近20个交易日涨跌幅（%）"""
    vals = [p["value"] for p in (pts or []) if isinstance(p, dict) and p.get("value") is not None]
    if len(vals) < 21:
        return None
    base, last = vals[-21], vals[-1]
    if not base:
        return None
    return (last / base - 1) * 100

def _tech_20d(pts):
    """V2 技术面段：MA5/10/20 + 5日/20日涨跌幅 + 20日高低点 + 量趋势"""
    vals = [p["value"] for p in (pts or []) if isinstance(p, dict) and p.get("value") is not None]
    vols = [p["volume"] for p in (pts or []) if isinstance(p, dict) and p.get("volume") is not None]
    if len(vals) < 21:
        return None
    def _ma(n):
        v = vals[-n:]
        return sum(v) / len(v)
    ma5, ma10, ma20 = _ma(5), _ma(10), _ma(20)
    last = vals[-1]
    chg5 = (last / vals[-6] - 1) * 100 if len(vals) >= 6 else None
    chg20 = (last / vals[-21] - 1) * 100
    hi20, lo20 = max(vals[-20:]), min(vals[-20:])
    pos = (last - lo20) / (hi20 - lo20) * 100 if hi20 > lo20 else 50
    vol_t = ""
    if len(vols) >= 6:
        v5, v20v = sum(vols[-5:]) / 5, (sum(vols[-20:]) / 20) if len(vols) >= 20 else sum(vols) / len(vols)
        if v20v > 0:
            vol_t = f"，近5日均量{'放' if v5 > v20v * 1.1 else ('缩' if v5 < v20v * 0.9 else '平')}（5日均量/20日均量={v5 / v20v:.2f}）"
    ma_line = " > ".join(f"MA{i}={ma:,.0f}" for i, ma in [(5, ma5), (10, ma10), (20, ma20)])
    trend = "多头排列" if ma5 > ma10 > ma20 else ("空头排列" if ma5 < ma10 < ma20 else "均线纠缠")
    return (f"MA5/10/20: {ma_line}（{trend}）｜ 现价{last:,.0f}："
            f"5日{chg5:+.1f}%、20日{chg20:+.1f}%｜ 20日区间{lo20:,.0f}~{hi20:,.0f}（现价位于区间{pos:.0f}%分位）"
            f"{vol_t}（数据源: 知几Guan日K）")

def _macro_section(macro):
    """V2 宏观投喂段：6金属20日涨跌 + 板块 + 相对强弱 + 利率/PMI + 跨品种比价"""
    if not isinstance(macro, dict) or macro.get("error"):
        return ""
    metals = macro.get("metals") or {}
    sec = macro.get("sectors") or {}
    mac = macro.get("macro") or {}
    parts = ["### 宏观与跨品种（β vs α 归因用）"]
    # 6金属近20日涨跌（从日K序列直接算，不用5日快照）
    met20 = [f"{k} {v:+.1f}%" for k, v in
             ((k, _pct_20d(v)) for k, v in metals.items()) if v is not None]
    if met20:
        parts.append("- 6金属近20日涨跌: " + " | ".join(met20) + "（数据源: 知几Guan日K）")
    zn_vs = _pct_20d(sec.get("zn_vs_sector"))
    ew = _pct_20d(sec.get("equal_weight_6m"))
    if zn_vs is not None and ew is not None:
        rel = "跑赢" if zn_vs > ew else "跑输"
        parts.append(f"- 锌相对有色板块: 锌{zn_vs:+.1f}% vs 6金属等权{ew:+.1f}% → 锌{rel}板块（差值{zn_vs - ew:+.1f}pct）")
    us10, cn10, pmi = mac.get("us10y_last"), mac.get("cn10y_last"), mac.get("cn_pmi_last")
    if isinstance(us10, dict) and us10.get("value") is not None:
        line = f"- 美债10Y: {us10['value']}%（{us10.get('date','')}，较上期{us10.get('chg',0):+.2f}）"
        if isinstance(cn10, dict) and cn10.get("value") is not None:
            line += f" | 中债10Y: {cn10['value']}%"
        if isinstance(pmi, dict) and pmi.get("value") is not None:
            line += f" | 中国制造业PMI: {pmi['value']}（{pmi.get('date','')}）"
        line += "（数据源: 知几料API）"
        parts.append(line)
    ratios = macro.get("ratios") or {}
    rcu, ral = _pct_20d(ratios.get("zn_cu")), _pct_20d(ratios.get("zn_al"))
    if rcu is not None or ral is not None:
        cu_s = "N/A" if rcu is None else f"{rcu:+.1f}%（{'跑赢' if rcu > 0 else '跑输'}铜）"
        al_s = "N/A" if ral is None else f"{ral:+.1f}%（{'跑赢' if ral > 0 else '跑输'}铝）"
        parts.append(f"- 跨品种比价20日变化: 锌/铜 {cu_s} | 锌/铝 {al_s}")
    if len(parts) == 1:
        return ""
    return "\n".join(parts)

def _load_contradiction_framework():
    """读取 zinc_scoring.yaml 的 contradictions，格式化为投喂给 AI 的核心矛盾框架。"""
    try:
        import yaml, os
        p = os.path.join(BASE_DIR, "zinc_scoring.yaml")
        with open(p, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        items = cfg.get("contradictions") or []
        rows = []
        for c in items:
            if isinstance(c, dict):
                rows.append((c.get("weight", 0), c.get("name", "?"),
                             c.get("bullish", []), c.get("bearish", [])))
        rows.sort(reverse=True, key=lambda x: x[0])
        lines = []
        for i, (w, name, bull, bear) in enumerate(rows, 1):
            b = " / ".join(str(x) for x in bull[:3]) if bull else "-"
            r = " / ".join(str(x) for x in bear[:3]) if bear else "-"
            lines.append(f"{i}. {name}（权重{w}）：利多[{b}]；利空[{r}]")
        return "\n".join(lines) if lines else "（无矛盾框架）"
    except Exception as e:
        print(f"[analyze] 矛盾框架加载失败: {e}")
        return "（矛盾框架加载失败）"


def _v2_prompt_template(b1, b1_t, b2, b2_t, b4, b4_t, a3_bean, a3_shfe,
                        a1_inv, a1_inv_t, a1_reg, a1_canc, b11_in, b11_out,
                        b5_18, b5_18_t, b5_27, b5_27_t, b6, b6_t,
                        b7, b7_t, b8_prod, b8_cap, b9_rate, b9_rate_t, b9_prod, b9_cap,
                        a2_npi, a2_magma, a4_profit, b12, b12_t, b10, b14_cr, b14_cr_t,
                        b3, b3_t, b13_pos, b13_fl, b13_cl, b13_cs,
                        nl, rp, weight_note, tech_line, macro_line, contradiction_framework,
                        contra_inject, contra_directive):
    """V2 prompt 模板（2026-08-16 试点版，学习锌报告可取之处）"""
    return f"""你是一位专业的锌(Zn)期货分析师。请根据以下数据，按【6步框架】给出实时解盘。

## 一、输入数据

### 基准价格
- 沪锌SHFE结算价: {fmt(b1,"元/吨")}（近5日:{b1_t}，变化:{trend_str(b1_t)}）
- LME锌现货结算价: {fmt(b2,"美元/吨")}（近5日:{b2_t}，变化:{trend_str(b2_t)}）
- 沪伦比: {fmt(b4,"")}（近5日:{b4_t}，<0.96进口窗口打开）
- 进口锌精矿TC: {fmt(a3_bean,"美元/干吨")}（矿端核心指标，下行=矿紧=冶炼亏损=利多） / 沪锌结算: {fmt(a3_shfe,"元/吨")}
{tech_line}

### LME库存与仓单
- LME总库存: {fmt(a1_inv,"吨")}（变化:{trend_str(a1_inv_t)}）
- 注册仓单: {fmt(a1_reg,"吨")} | 注销仓单: {fmt(a1_canc,"吨")}
- LME入库: {fmt(b11_in,"吨")} | 出库: {fmt(b11_out,"吨")}

### 国内库存
- 国内8省锌锭库存: {fmt(b5_18,"吨")}（变化:{trend_str(b5_18_t)}）
- 锌锭现货库存(中国日度): {fmt(b5_27,"吨")}（变化:{trend_str(b5_27_t)}）

### 矿端与冶炼供给
- 进口锌精矿TC: {fmt(b6,"美元/干吨")}（变化:{trend_str(b6_t)}，下行=矿紧=利多）
- 精炼锌月产量: {fmt(b8_prod,"万吨/月")} | 产能利用率: {fmt(b8_cap,"%")}
- 锌锭进口盈亏(不含税): {fmt(b7,"元/吨")}（变化:{trend_str(b7_t)}，负值=进口窗口关闭）

### 进口窗口
- 锌锭进口盈亏(不含税): {fmt(a2_magma,"元/吨")} | 进口占比: {fmt(a2_npi,"%")} | 含税进口盈亏: {fmt(a4_profit,"元/吨")}

### 需求侧
- 镀锌板周产量: {fmt(b9_prod,"万吨")}（占锌消费60%+，需求核心指标）
- 表观消费: {fmt(b12,"万吨/月")}（变化:{trend_str(b12_t)}）
- 锌合金开工率: {fmt(b9_rate,"%")}（变化:{trend_str(b9_rate_t)}）
- 广东0#锌锭升贴水: {fmt(b14_cr,"元/吨")}（变化:{trend_str(b14_cr_t)}，升水走扩=需求回暖）

### 资金面
- SHFE持仓: {fmt(b3,"手")}（变化:{trend_str(b3_t)}）
- LME持仓: {fmt(b13_pos,"手")} | 基金多头: {fmt(b13_fl,"手")}
- 商业多头: {fmt(b13_cl,"手")} | 商业空头: {fmt(b13_cs,"手")}

{macro_line}

### 市场核心矛盾框架（来自 zinc_scoring.yaml，按权重降序；优先识别这些矛盾）
{contradiction_framework}

### 机器实时识别矛盾（L2引擎，按强度降序；结合上方数据实时算出，证据链见各条 strength/置信）
{contra_inject}

### 机器强制方向指令（L2引擎基于底层数据 high-confidence 判定，请在【结论】与【多空对比】中优先采纳并明确体现，勿与下方方向冲突）
{contra_directive}

### 产业资讯
{nl}

### 研报观点
{rp if rp else "暂无研报观点"}

## 二、分析流程（思维链·内部完成）

### 第1步：信号分类
将上方各指标逐一归类为利多或利空信号，标注强弱（强/中/弱）。

### 第2步：权重打分
{weight_note}
→ 计算多空加权总分，得出方向判断。

### 第3步：核心矛盾识别
找出当前权重最高且边际变化最大的1-2个矛盾点。

### 第4步：β vs α 归因
结合宏观与跨品种数据，判断本轮涨跌中：
- β（宏观/板块β）：美债利率、PMI、6金属板块整体走势解释了多大比例？
- α（锌自身α）：库存/冶炼利润/需求等锌自身供需解释了多大比例？
→ 一句话给出"β主导 / α主导 / 共振"的归因结论。

### 第5步：因果推演与交叉验证
从核心矛盾推导价格传导链条；用其他指标交叉验证，标记冲突信号。

**以上步骤在内部完成，不输出中间过程。**

## 三、最终输出（结构化研报，面向客户）

**【结论】**偏多/偏空/中性（一句话概括行情阶段+核心矛盾，20字以内）

**【区间预判】**根据技术面20日区间+供需矛盾强度，给出短期价格区间（XX,XXX~XX,XXX元/吨），说明区间依据

**【核心矛盾】**当前最核心的供需矛盾是什么，用数据支撑（1-2条，每条50字以内）

**【β vs α 归因】**（一句话归因结论）

**【多空对比】**
- 利多：信号1（强度·验证状态）；信号2（强度·验证状态）
- 利空：信号1（强度·验证状态）；信号2（强度·验证状态）

**【跨品种对比】**锌 vs 铜/铝/锌的相对强弱及传导含义（1-2条）

**【风险】**3-5条具体证伪路径（"若X发生→Y逻辑被证伪→价格方向"，每条40字以内）

**【建议】**方向 + 关键价位（支撑/阻力） + 确认条件 + 止损触发 + 置信度（高/中/低，给出理由）

**【资讯与研报】**从上方产业资讯和研报观点中提炼3-5条最核心的信息，每条格式：`[事件/观点] → [影响方向] → [对锌价影响]`，控制在3句话以内。**重要：仅引用与锌供需/价格直接相关的资讯，与锌无关的新闻（如纯政治事件、与锌无关的商品）禁止引用。**

## 四、硬约束
1. 所有数据必须来自输入，禁止编造
2. 明确给出"偏多/偏空/中性"判断，禁止模棱两可
3. N/A的数据标注"缺失"，不要推测
4. 每条风险必须有具体触发条件
5. 结论与多空信号方向必须一致
6. 输出控制在800字以内
7. **区间预判必须给出具体数字范围，置信度必须说明理由**"""

# ── V2 Prompt（试点改版 2026-08-16：学习锌报告可取之处）──
# 相对 V1 的改动：
#  ① 宏观投喂（6金属/板块/美债/PMI/跨品种比价 → β vs α 归因）
#  ② 技术面段（MA5/10/20、5日/20日涨跌、20日区间分位、量趋势，本地日K计算）
#  ③ 结论前置（前3行给一行结论+区间预判+置信度）
#  ④ 硬性输出「区间预判+明确触发条件」
#  ⑤ 跨品种对比 ⑥ 数据源标注 ⑦ 新闻相关性硬约束（无关新闻禁止引用）
#  ⑧ 生成后数字校验闸门 validate_numbers()
def build_prompt_v2(charts, news, reports, macro=None):
    # 新闻新鲜度标注（与V1相同）
    def _age_hours(time_str):
        if not time_str:
            return "?"
        try:
            ts = time_str.replace("T", " ")[:16]
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
            diff = (datetime.now() - dt).total_seconds() / 3600
            return f"{diff:.0f}h" if diff < 24 else f"{diff/24:.1f}d"
        except Exception:
            return "?"
    def _dir_tag(n):
        d = n.get("direction")
        return "利多" if d == "bullish" else ("利空" if d == "bearish" else "")
    nl = "\n".join(f"[{n.get('level','C')}|{n.get('score',0)}分|{_dir_tag(n)}] {n.get('title','')} ({n.get('source','')} | {n.get('time','')} | 距今{_age_hours(n.get('time',''))})" for n in (news or [])[:15])
    rp = "\n".join(f"[研报] {r.get('title','')}: {r.get('body','')[:100]} ({r.get('time','')})" for r in (reports or [])[:8])

    # 提取18个指标（与V1完全同源）
    a1_inv, a1_inv_t = gv("A1_lme_inventory", "inventory", charts)
    a1_reg, _ = gv("A1_lme_inventory", "registered", charts)
    a1_canc, _ = gv("A1_lme_inventory", "cancelled", charts)
    a2_ratio, a2_ratio_t = gv("A2_import_window", "shfe_lme_ratio", charts)
    a2_magma, _ = gv("A2_import_window", "magma_discount", charts)
    a2_npi, _ = gv("A2_import_window", "import_ratio", charts)
    a3_bean, _ = gv("A3_substitution", "zinc_bean", charts)
    a3_shfe, _ = gv("A3_substitution", "shfe_settle", charts)
    a4_profit, a4_profit_t = gv("A4_smelting_pressure", "profit", charts)
    b1, b1_t = gv("B1_shfe_price", charts=charts)
    b2, b2_t = gv("B2_lme_price", charts=charts)
    b3, b3_t = gv("B3_shfe_oi", charts=charts)
    b4, b4_t = gv("B4_ratio", charts=charts)
    b5_18, b5_18_t = gv("B5_china_inventory", "inv_18", charts)
    b5_27, b5_27_t = gv("B5_china_inventory", "inv_27", charts)
    b6, b6_t = gv("B6_zinc_concentrate_tc", charts=charts)
    b7, b7_t = gv("B7_smelting_profit", charts=charts)
    b8_prod, _ = gv("B8_china_production", "chinese_prod", charts)
    b8_cap, _ = gv("B8_china_production", "chinese_cap", charts)
    b9_prod, _ = gv("B9_galvanizing", "galvanized_prod", charts)
    b9_cap, _ = gv("B9_galvanizing", "apparent_cons", charts)
    b9_rate, b9_rate_t = gv("B9_galvanizing", "alloy_rate", charts)
    b10, b10_t = gv("B10_sulfate_price", charts=charts)
    b11_out, _ = gv("B11_lme_flow", "outflow", charts)
    b11_in, _ = gv("B11_lme_flow", "inflow", charts)
    b12, b12_t = gv("B12_apparent_consumption", charts=charts)
    b13_pos, _ = gv("B13_lme_funding", "position", charts)
    b13_fl, _ = gv("B13_lme_funding", "fund_long", charts)
    b13_cl, _ = gv("B13_lme_funding", "comm_long", charts)
    b13_cs, _ = gv("B13_lme_funding", "comm_short", charts)
    b14_cr, b14_cr_t = gv("B14_premium", "guangdong_premium", charts)

    # V2 新增：技术面 + 宏观（数据源标注已在段内）
    tech_ni = _tech_20d(charts.get("B1_shfe_price") or [])
    macro_block = _macro_section(macro)

    # ── 动态权重调整（与V1相同）──
    def _volatility(vals):
        if len(vals) < 3:
            return 0
        avg = sum(vals) / len(vals)
        if avg == 0:
            return 0
        return (sum((v - avg) ** 2 for v in vals) / len(vals)) ** 0.5 / abs(avg)
    supply_vol = _volatility(b7_t) + _volatility(b9_rate_t)
    inventory_vol = _volatility(a1_inv_t) + _volatility(b5_18_t)
    demand_vol = _volatility(b12_t) + _volatility(b14_cr_t)
    capital_vol = _volatility(b3_t) if b3_t else 0
    max_vol = max(supply_vol, inventory_vol, demand_vol, capital_vol, 0.001)
    w_supply = max(20, min(45, int(35 + (supply_vol / max_vol - 0.5) * 15)))
    w_inventory = max(15, min(35, int(25 + (inventory_vol / max_vol - 0.5) * 15)))
    w_demand = max(10, min(30, int(20 + (demand_vol / max_vol - 0.5) * 10)))
    w_capital = max(5, min(25, int(15 + (capital_vol / max_vol - 0.5) * 15)))
    w_info = max(5, 100 - w_supply - w_inventory - w_demand - w_capital)
    weight_note = f"当前动态权重：供给{w_supply}% | 库存{w_inventory}% | 需求{w_demand}% | 资金{w_capital}% | 资讯{w_info}%"

    tech_line = f"- SHFE锌技术面(日K): {tech_ni}" if tech_ni else "- SHFE锌技术面(日K): 数据缺失（不足21个交易日）"
    macro_line = macro_block if macro_block else "### 宏观与跨品种\n- 宏观数据缺失（本轮未投喂）"
    contradiction_framework = _load_contradiction_framework()
    # ── L4 接入：跑 L2 引擎，把机器实时识别的矛盾注入 prompt ──
    live_contra = run_engine(charts, news=news)
    contra_inject = format_for_prompt(live_contra)
    # 强指令：高置信方向 → 强制模型在结论中采纳（解决"机器段只是辅助、模型不听"的问题）
    strong = [c for c in live_contra if c.get("direction") != 0 and c.get("confidence", 0) >= 0.6]
    if strong:
        contra_directive = "\n".join(
            f"- {c['name']}：{'利多' if c['direction'] == 1 else '利空'}"
            f"（置信{c.get('confidence', 0)}，策略{c.get('strategy', '')}）"
            for c in strong)
    else:
        contra_directive = "（当前机器未识别到高置信方向，请基于上方数据自行判断）"
    return _v2_prompt_template(
        b1, b1_t, b2, b2_t, b4, b4_t, a3_bean, a3_shfe, a1_inv, a1_inv_t,
        a1_reg, a1_canc, b11_in, b11_out, b5_18, b5_18_t, b5_27, b5_27_t,
        b6, b6_t, b7, b7_t, b8_prod, b8_cap, b9_rate, b9_rate_t, b9_prod, b9_cap,
        a2_npi, a2_magma, a4_profit, b12, b12_t, b10, b14_cr, b14_cr_t, b3, b3_t,
        b13_pos, b13_fl, b13_cl, b13_cs, nl, rp, weight_note, tech_line, macro_line, contradiction_framework,
        contra_inject, contra_directive)

# ── Call AI (ZSUN primary, DashScope fallback) ──
def _load_env_keys():
    keys = {}
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys

def call_ai(prompt, key):
    env_keys = _load_env_keys()

    # 1) DashScope（阿里百炼）优先 — 稳定可用
    dash_key = env_keys.get("DASHSCOPE_KEY", "")
    dash_model = env_keys.get("DASHSCOPE_MODEL", DASHSCOPE_MODEL)
    if dash_key:
        try:
            payload = {"model": dash_model, "messages": [
                {"role":"system","content":"你是专业锌期货分析师，输出结构化研报，面向客户展示。"},
                {"role":"user","content": prompt}
            ], "max_tokens": 4096, "temperature": 0.7}
            req = urllib.request.Request(DASHSCOPE_URL, data=json.dumps(payload).encode(),
                headers={"Content-Type":"application/json","Authorization": f"Bearer {dash_key}"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            msg = result["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return {
                "content": content,
                "model": dash_model,
                "usage": result.get("usage", {}),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "provider": "dashscope"
            }
        except Exception as e:
            print(f"[analyze.py] DashScope failed: {e}, falling back to ZSUN")

    # 2) ZSUN 备选
    zsun_key = key or env_keys.get("ZSUN_KEY", "")
    if zsun_key:
        try:
            payload = {"model": ZSUN_MODEL, "messages": [
                {"role":"system","content":"你是专业锌期货分析师，输出结构化研报，面向客户展示。"},
                {"role":"user","content": prompt}
            ], "max_tokens": 1500, "temperature": 0.7}
            req = urllib.request.Request(ZSUN_URL, data=json.dumps(payload).encode(),
                headers={"Content-Type":"application/json","Authorization": f"Bearer {zsun_key}"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            msg = result["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return {
                "content": content,
                "model": ZSUN_MODEL,
                "usage": result.get("usage", {}),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "provider": "zsun"
            }
        except Exception as e:
            print(f"[analyze.py] ZSUN failed: {e}")
    
    return {"error": "所有 AI 供应商均不可用", "content": "", "model": "", "usage": {}, "timestamp": "", "provider": ""}

# ── Main entry: generate full real-time analysis ──
def analyze(key):
    data = load_data()
    if not data:
        return {"error": "无法加载 data.json 数据"}
    charts = data.get("charts", {})
    news = fetch_news()
    reports = fetch_reports()
    prompt = build_prompt_active(charts, news, reports, macro=None)
    ai_result = call_ai(prompt, key)
    # 提取方向
    content = ai_result["content"]
    ai_dir = "偏多" if "偏多" in content[:300] else ("偏空" if "偏空" in content[:300] else ("中性" if "中性" in content[:300] else "未知"))
    return {
        "ai_analysis": content,
        "ai_direction": ai_dir,
        "news": news[:15],
        "reports": reports[:8],
        "model": ai_result["model"],
        "usage": ai_result["usage"],
        "timestamp": ai_result["timestamp"],
        "prompt": prompt
    }
