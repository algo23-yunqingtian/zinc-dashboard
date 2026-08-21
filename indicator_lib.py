#!/usr/bin/env python3
"""
indicator_lib — L1 指标标准化库（锌 Zn）
────────────────────────────────────────
供 contradiction_engine.py / analyze_zn.py 消费：
  SERIES_REGISTRY: 逻辑名 -> (源chart, 字段)  的扁平序列注册表
  get_series(charts, name) -> (显示名, values[])
  prefilter(charts, z_thr, min_len) -> [{name, series}]
  zscore(values) -> 最近z
  cusum_flag(values) -> (flag, cusum_z)
  direction(values) -> (sign, pct, latest)
"""
from __future__ import annotations
import math, statistics
from typing import List, Dict, Tuple, Optional, Any

# ── 序列注册表：逻辑名 → (chart 键, 字段路径) ──────────────────────────
# 字段路径支持嵌套: "subkey" 或 ""（取 chart 本身为 series 列表）
SERIES_REGISTRY: Dict[str, Tuple[str, str, str]] = {
    # 价格
    "shfe_price":      ("B1_shfe_price", "", "SHFE锌主力"),
    "lme_price":       ("B2_lme_price", "", "LME锌3M"),
    "shfe_oi":         ("B3_shfe_oi", "", "SHFE持仓"),
    "shfe_lme_ratio":  ("B4_ratio", "", "沪伦比"),
    # 库存
    "lme_inv":         ("A1_lme_inventory", "inventory", "LME库存"),
    "lme_reg":         ("A1_lme_inventory", "registered", "LME注册仓单"),
    "lme_canc":        ("A1_lme_inventory", "cancelled", "LME注销仓单"),
    "lme_outflow":     ("B11_lme_flow", "outflow", "LME流出"),
    "lme_inflow":      ("B11_lme_flow", "inflow", "LME流入"),
    "inv_18":          ("B5_china_inventory", "inv_18", "七地库存"),
    "inv_27":          ("B5_china_inventory", "inv_27", "27地库存"),
    "bean_inv":        ("B6_bean_inventory", "", "锌锭社会库存"),
    # 冶炼/成本
    "smelt_profit":    ("A4_smelting_pressure", "profit", "冶炼利润"),
    "tc":              ("A4_smelting_pressure", "profit", "TC加工费(代理)"),  # 无独立TC序列，用利润近似
    "smelt_pressure":  ("A4_smelting_pressure", "profit", "冶炼压力"),
    "chinese_prod":    ("B8_china_production", "chinese_prod", "中国精锌产量"),
    "chinese_cap":     ("B8_china_production", "chinese_cap", "中国精锌产能"),
    # 需求/下游
    "galvanized_prod": ("B8_china_production", "chinese_prod", "镀锌/精锌产量"),
    "galvanized_rate": ("B9_indonesia", "indonesia_rate", "镀锌开工率(代理)"),  # 印尼开工率代理
    "apparent_cons":   ("B12_apparent_consumption", "", "表观消费"),
    # 升贴水/期货结构
    "magma_discount":  ("A2_import_window", "magma_discount", "进口盈亏"),
    "sulfate_price":   ("B10_sulfate_price", "", "硫酸价格"),
}

# 反向：chart 键 -> 逻辑名（供 prefilter 枚举）
CHART_TO_SERIES: Dict[str, List[str]] = {}
for _ln, (_ck, _fk, _dn) in SERIES_REGISTRY.items():
    CHART_TO_SERIES.setdefault(_ck, []).append(_ln)


def _series_of(chart: Any, field: str):
    """从 chart 对象取值：field 空 -> chart 本身(list of {date,value})；
    否则取 chart[field]（list of {date,value}）。"""
    if field == "":
        return chart
    if isinstance(chart, dict):
        return chart.get(field, [])
    return []


def _to_values(series) -> List[float]:
    out = []
    if isinstance(series, list):
        for it in series:
            if isinstance(it, dict):
                v = it.get("value")
                if v is not None:
                    out.append(float(v))
            else:
                out.append(float(it))
    return out


# ── 接口 ────────────────────────────────────────────────────────────
def get_series(charts: Dict, name: str) -> Tuple[str, List[float]]:
    """按逻辑名取序列 -> (显示名, values[])"""
    if name not in SERIES_REGISTRY:
        return name, []
    ck, fk, dn = SERIES_REGISTRY[name]
    chart = charts.get(ck, {})
    return dn, _to_values(_series_of(chart, fk))


def prefilter(charts: Dict, z_thr: float = 1.2, min_len: int = 5) -> List[Dict]:
    """枚举注册表中有足够长度的序列 -> [{name, series}]"""
    out = []
    for ln, (ck, fk, dn) in SERIES_REGISTRY.items():
        chart = charts.get(ck, {})
        vals = _to_values(_series_of(chart, fk))
        if len(vals) >= min_len:
            out.append({"name": ln, "series": vals, "display": dn})
    return out


def zscore(values: List[float]) -> float:
    """最近值标准化 z = (last - mean)/std；数据不足/零方差返回 0。"""
    if len(values) < 3:
        return 0.0
    mean = sum(values) / len(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    if sd == 0:
        return 0.0
    return round((values[-1] - mean) / sd, 4)


def cusum_flag(values: List[float], k=0.5, h=4.0) -> Tuple[bool, float]:
    """CUSUM 双侧突变检测：正向(均值漂移↑) C+/ 负向 C-。
    返回 (是否触发, 当前累计z)。"""
    if len(values) < 10:
        return False, 0.0
    mean = sum(values[:max(3, len(values) // 2)]) / max(3, len(values) // 2)
    sd = statistics.stdev(values[:max(3, len(values) // 2)]) if len(values) > 4 else 0.0
    if sd == 0:
        return False, 0.0
    c_plus = c_minus = 0.0
    for v in values:
        z = (v - mean) / sd
        c_plus = max(0.0, c_plus + z - k)
        c_minus = max(0.0, c_minus - z - k)
    cz = max(c_plus, c_minus)
    return (cz > h), round(cz, 4)


def direction(values: List[float], pct_window: int = 5) -> Tuple[int, float, float]:
    """最近 pct_window 个点线性斜率方向：
    返回 (sign, 最近变动%, 最新值)。sign: +1涨/-1跌/0平。"""
    if len(values) < 2:
        return 0, 0.0, values[-1] if values else 0.0
    win = max(2, min(pct_window, len(values)))
    base = values[-win]
    last = values[-1]
    pct = round((last - base) / base * 100.0, 2) if base else 0.0
    # 简单线性回归斜率方向
    xs = list(range(win))
    ys = values[-win:]
    n = win
    sx = sum(xs); sy = sum(ys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / denom if denom else 0.0
    rel = abs(slope / (abs(last) + 1e-9))
    sign = 1 if slope > 0.0005 else (-1 if slope < -0.0005 else 0)
    return sign, pct, last


if __name__ == "__main__":
    # 自测
    import json, os
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    d = json.load(open(fp))
    charts = d["charts"]
    print("prefilter 序列数:", len(prefilter(charts)))
    for nm in ["shfe_price", "lme_inv", "smelt_profit", "tc", "galvanized_prod"]:
        dn, vals = get_series(charts, nm)
        print(f"  {nm} -> {dn}: len={len(vals)} last={vals[-1] if vals else None} sign={direction(vals)[0]} z={zscore(vals)}")