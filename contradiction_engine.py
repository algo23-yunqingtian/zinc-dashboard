#!/usr/bin/env python3
"""
L2 矛盾识别引擎 (contradiction_engine)
──────────────────────────────────────
多策略并行识别矛盾，消费 L1(indicator_lib) + zinc_scoring.yaml：
  ① Rule        规则型：yaml 矛盾 × 新闻命中关键词 → 激活该矛盾
  ② Anomaly     统计异常：单序列 z 越界 / CUSUM 突变
  ③ Divergence  背离型：逻辑应同向却反向（伪突破/假紧张）

每条矛盾输出统一结构：
  {id, strategy, name, strength(0-1), direction(+1/-1/0),
   evidence:[{name,z,pct,sign,latest}], confidence}
run_engine() 返回按 strength 降序的列表；format_for_prompt() 产出注入文本。
"""
import os
from indicator_lib import (
    SERIES_REGISTRY, get_series, direction, zscore, cusum_flag, prefilter,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(BASE_DIR, "zinc_scoring.yaml")

# 背离对：逻辑"应反向"，同向↑ 即背离（假突破/假紧张 → 利空）
#   价涨却累库=伪突破 / 开工升产量降=需求假象 / 注销升却累库=假紧张
_DIVERGE_SAME = [
    ("shfe_price", "lme_inv", "价涨却累库=伪突破"),
    ("galvanized_rate", "galvanized_prod", "开工升产量降=需求假象"),
    ("lme_canc", "lme_inv", "注销升却累库=假紧张"),
]
# 矿端特殊背离：TC降(矿紧利多) 但 冶炼利润升(未受压) → 矿紧信号被证伪
_DIVERGE_MINE = ("tc", "smelt_profit")


def _latest(values):
    return values[-1] if values else None


def _signal_direction(c, charts):
    """数据代理方向：读 yaml signal{series,trend,direction}，用底层序列趋势判多空。
    仅当趋势匹配(trend=down 且序列 sign=-1 / trend=up 且 sign=+1)时返回配置方向，否则 0。
    charts 为 None 时返回 0（保持无图不强行判方向）。"""
    sig = c.get("signal")
    if not sig or charts is None:
        return 0
    ser = sig.get("series")
    if not ser:
        return 0
    _, v = get_series(charts, ser)
    if len(v) < 3:
        return 0
    sgn, _, _ = direction(v)
    want = 1 if sig.get("trend") == "up" else (-1 if sig.get("trend") == "down" else 0)
    if want != 0 and sgn == want:
        return sig.get("direction", 0)
    return 0


# ── ① Rule 规则型：yaml 矛盾 × 新闻命中（+ 数据代理方向）──
def _strategy_rule(news, charts=None, yaml_path=YAML_PATH):
    """news: list of dict(含 title/body)。charts: data.json.charts（用于数据代理方向）。
    返回矛盾列表。无 yaml 或无 news 时返回 []。"""
    try:
        import yaml
        cfg = yaml.safe_load(open(yaml_path, encoding="utf-8"))
        items = cfg.get("contradictions") or []
    except Exception:
        return []
    if not news:
        return []
    blob = " ".join(
        str(n.get("title", "")) + " " + str(n.get("body", "")) for n in news
    )
    out = []
    for c in items:
        if not isinstance(c, dict):
            continue
        kws = (c.get("bullish") or []) + (c.get("bearish") or []) + (c.get("news_keywords") or [])
        hits = sum(1 for k in kws if k and k in blob)
        if hits == 0:
            continue
        # 判断多/空：命中 bullish 多→利多，bearish 多→利空
        bull_h = sum(1 for k in (c.get("bullish") or []) if k and k in blob)
        bear_h = sum(1 for k in (c.get("bearish") or []) if k and k in blob)
        dr = 1 if bull_h > bear_h else (-1 if bear_h > bear_h else 0)
        evidence = [{"news_hits": hits}]
        # 数据代理方向：新闻没给方向时，用图表趋势补一个（即使新闻给了也记录佐证）
        sig_dir = _signal_direction(c, charts)
        if sig_dir != 0:
            sig = c.get("signal") or {}
            if dr == 0:
                dr = sig_dir
            evidence.append({"data_signal": sig.get("series"),
                             "trend": sig.get("trend"), "direction": sig_dir})
        out.append({
            "id": c.get("id", "rule"), "strategy": "rule",
            "name": c.get("name", "?"),
            "strength": round(min(1.0, hits / 3), 3),
            "direction": dr, "evidence": evidence,
            "confidence": round(min(1.0, hits / 2), 3),
        })
    return out


# ── ② Anomaly 统计异常：z 越界 / CUSUM 突变 ──
def _strategy_anomaly(charts, z_thr=2.0, pct_thr=35.0):
    out = []
    for nm in [p["name"] for p in prefilter(charts, z_thr=1.2)]:
        d, v = get_series(charts, nm)
        if len(v) < 5:
            continue
        z = zscore(v)
        flag, cz = cusum_flag(v)
        sgn, pct, _ = direction(v)
        # 触发：z 越界 / CUSUM 突变 / 极端单期跳变(pct>=35%，趋势性下跌不算)
        is_spike = abs(pct) >= pct_thr
        if abs(z) >= z_thr or flag or is_spike:
            strength = round(min(1.0, max(abs(z) / 3, abs(pct) / 30)), 3)
            conf = round(min(1.0, max(len(v) / 60, 0.65)), 3)
            out.append({
                "id": f"anomaly_{nm}", "strategy": "anomaly",
                "name": f"异常波动·{nm}",
                "strength": strength,
                "direction": sgn,
                "evidence": [{"name": nm, "z": round(z, 3), "pct": pct,
                              "sign": sgn, "latest": _latest(v), "cusum_z": cz}],
                "confidence": conf,
                "series": v,  # 底层序列，供去重/前端溯源（注入 prompt 时由 format_for_prompt 忽略）
            })
    return out


# ── ③ Divergence 背离型：逻辑应同向却反向 ──
def _strategy_divergence(charts):
    out = []
    # 通用"应反向、同向↑ 才判背离（假信号→利空）"
    for a, b, note in _DIVERGE_SAME:
        da, va = get_series(charts, a)
        db, vb = get_series(charts, b)
        if len(va) < 3 or len(vb) < 3:
            continue
        sa, pa, _ = direction(va)
        sb, pb, _ = direction(vb)
        if not (sa == 1 and sb == 1):
            continue  # 非同向↑ → 不判背离
        strength = round(min(1.0, (abs(pa) + abs(pb)) / 20), 3)
        out.append({
            "id": f"diverge_{a}_{b}", "strategy": "divergence",
            "name": f"背离·{a} vs {b}",
            "strength": strength, "direction": -1,
            "evidence": [{"name": a, "pct": pa, "sign": sa, "latest": _latest(va)},
                         {"name": b, "pct": pb, "sign": sb, "latest": _latest(vb)}],
            "confidence": 0.6, "note": note,
        })
    # 矿端特殊：TC降 但 利润升 → 矿紧未传导
    dt, vt = get_series(charts, "tc")
    dp, vp = get_series(charts, "smelt_profit")
    if len(vt) >= 3 and len(vp) >= 3:
        stc, ptc, _ = direction(vt)
        spr, ppr, _ = direction(vp)
        if stc == -1 and spr == 1:
            out.append({
                "id": "diverge_tc_profit", "strategy": "divergence",
                "name": "矿紧未传导利润",
                "strength": round(min(1.0, (abs(ptc) + abs(ppr)) / 20), 3),
                "direction": -1,
                "evidence": [{"name": "tc", "pct": ptc, "sign": stc, "latest": _latest(vt)},
                             {"name": "smelt_profit", "pct": ppr, "sign": spr, "latest": _latest(vp)}],
                "confidence": 0.7, "note": "TC降(矿紧利多)但利润升，矿紧信号被证伪",
            })
    return out


def _series_val(p):
    """序列元素可能为 {date,value} 字典或裸标量，统一取数值。"""
    if isinstance(p, dict):
        return float(p.get("value", 0) or 0)
    try:
        return float(p)
    except Exception:
        return 0.0


def _dedup_by_series(contradictions):
    """合并基于同一底层序列的矛盾（如 lme_cancelled 同时填入 A1.cancelled 与
    B11.outflow，会被异常策略计两次）。按 (方向, 末8点数值签名) 去重，保留强者。"""
    seen = {}
    out = []
    for c in contradictions:
        v = c.get("series")
        if v and len(v) >= 3:
            try:
                sig = (c.get("direction"),
                       tuple(round(_series_val(p), 3) for p in v[-8:]))
            except Exception:
                sig = None
            if sig and sig in seen:
                prev = seen[sig]
                if c["strength"] > prev["strength"]:
                    prev["strength"] = c["strength"]
                    prev["id"] = f"{c['id']}|{prev['id']}"
                continue
            if sig:
                seen[sig] = c
        out.append(c)
    return out


def run_engine(charts, news=None):
    """跑全部策略，返回按 strength 降序的矛盾列表。"""
    res = []
    res += _strategy_anomaly(charts)
    res += _strategy_divergence(charts)
    res += _strategy_rule(news, charts)
    res.sort(key=lambda x: x["strength"], reverse=True)
    res = _dedup_by_series(res)
    return res


def format_for_prompt(contradictions, top=6):
    """把已识别矛盾格式化为注入 build_prompt_v2 的文本段。"""
    if not contradictions:
        return "（当前未识别到显著矛盾）"
    lines = []
    for i, c in enumerate(contradictions[:top], 1):
        dr = "利多" if c["direction"] == 1 else ("利空" if c["direction"] == -1 else "中性")
        lines.append(
            f"{i}. [{c['strategy']}] {c['name']}｜强度{c['strength']}｜方向{dr}｜"
            f"置信{c['confidence']}"
        )
    return "\n".join(lines)
