#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collab/verify_active_contradictions.py
—— 本地只读校验：自动识别矛盾的 "接线状态" 探测器（无需 API 密钥/网络）

做了什么：
  1) 读本地 data.json，检查 active_contradictions 字段是否已存在（验证 fetch_zn.py:main 是否真写了种子字段）。
  2) 用真实 charts 直接跑 contradiction_engine.run_engine（只需图表数据，不依赖新闻/AI 密钥），
     证明 L1+L2 引擎在真实数据上能识别矛盾，并展示它"本应"被注入 AI 解盘的模样。
  3) 校验输出结构是否符合前端/AI 注入所需 schema。

这是给 CodeBuddy 与 Hermes 共用的健康探针：每次想确认"自动矛盾识别"是否真的接通，跑一遍即可。
"""
import json
import os
import sys

# Windows 控制台默认 GBK，打印中文/特殊字符会 UnicodeEncodeError；强制 stdout 为 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
DATA = os.path.join(BASE, "data.json")

EXPECTED_KEYS = {"id", "strategy", "name", "strength", "direction", "evidence", "confidence"}


def main():
    print("== verify_active_contradictions ==")
    if not os.path.exists(DATA):
        print("[INFO] 本地无 data.json（尚未跑过 Actions fetch）。接线缺口无法直接验证，但引擎可离线自测。")
        _run_engine_offline()
        return

    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    print("[OK] data.json 存在，顶层键:", list(data.keys())[:15])

    ac = data.get("active_contradictions")
    print("[STATE] data.json 含 active_contradictions 字段:", ac is not None)
    if ac is not None:
        print("        现有条目数:", len(ac) if isinstance(ac, list) else "非list")
        if isinstance(ac, list) and ac:
            bad = [i for i, c in enumerate(ac) if not EXPECTED_KEYS.issubset(c)]
            print("        schema 合规条目:", len(ac) - len(bad), "/", len(ac))
    else:
        print("        [WARN] fetch_zn.py:main 尚未调用 run_engine 写入该字段（'接线'缺口）。")

    charts = data.get("charts", {}) or {}
    print("[STATE] charts 槽位数:", len(charts) if isinstance(charts, dict) else "n/a")
    _run_engine_offline(charts)


def _run_engine_offline(charts=None):
    try:
        from contradiction_engine import run_engine, format_for_prompt
    except Exception as e:
        print("[ERR] 引擎 import 失败:", repr(e))
        return
    if not charts:
        print("[SKIP] 无 charts 数据，跳过实时跑引擎。")
        return
    res = run_engine(charts, news=None)
    dr_map = {1: "利多", -1: "利空", 0: "中性"}
    print("\n== run_engine(charts) 实时结果（仅图表、无新闻）==")
    print("识别到矛盾条数:", len(res))
    for c in res[:8]:
        print("  %-28s str=%-5s dir=%-4s conf=%-5s [%s]" % (
            c["id"], c["strength"], dr_map.get(c["direction"], "?"),
            c["confidence"], c["strategy"]))
    print("\n== format_for_prompt（这是本应注入 AI 解盘的文本）==")
    print(format_for_prompt(res, top=6))
    ok = all(EXPECTED_KEYS.issubset(c) for c in res) if res else True
    print("\n[SCHEMA] 引擎输出结构合规:", ok)


if __name__ == "__main__":
    main()
