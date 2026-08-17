#!/usr/bin/env python3
"""锌矛盾筛选 · 低成本运维脚本（纯本地计算，0 次 Zhiji 调用）
用法:
  python collab/screen_zinc.py            # 筛选报告：8框架 + 实时命中
  python collab/screen_zinc.py --explain  # 仅打印"我们筛哪些矛盾"(yaml 8条)
  python collab/screen_zinc.py --regen    # 用本地 charts 重算 active_contradictions 写回 data.json
  python collab/screen_zinc.py --json     # 机器可读输出
依赖: indicator_lib / contradiction_engine / zinc_scoring.yaml（均无网络）
"""
import json, os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
from contradiction_engine import run_engine, format_for_prompt
import yaml

DATA = os.path.join(BASE, "data.json")
YAML = os.path.join(BASE, "zinc_scoring.yaml")


def _load():
    if not os.path.exists(DATA):
        print("ERR: data.json 不存在"); sys.exit(1)
    return json.load(open(DATA, encoding="utf-8"))


def explain():
    cfg = yaml.safe_load(open(YAML, encoding="utf-8"))
    print("== 锌市场 8 大核心矛盾（筛选框架·来自 zinc_scoring.yaml）==")
    for c in cfg.get("contradictions", []):
        print(f"  [{c.get('weight',0)}] {c.get('id')}: {c.get('name')}")
        print(f"        利多:{c.get('bullish')}")
        print(f"        利空:{c.get('bearish')}")


def _run():
    d = _load()
    charts = d.get("charts", {})
    news = (d.get("news") or {}).get("items", []) or []
    return run_engine(charts, news=news), charts


def screen():
    contra, _ = _run()
    print("== 实时筛选结果（按强度降序）==")
    print(format_for_prompt(contra))
    print(f"-- 共命中 {len(contra)} 条")
    for c in contra:
        ev = c.get("evidence", [])
        print(f"  · {c['id']} | 策略:{c['strategy']} | 强度:{c['strength']} | "
              f"方向:{c['direction']} | 置信:{c['confidence']}")
        for e in ev[:2]:
            print(f"      - {e}")
    return contra


def regen():
    contra, _ = _run()
    d = _load()
    lean = [{k: v for k, v in c.items() if k != "series"} for c in contra]
    d["active_contradictions"] = {
        "structured": lean,
        "formatted": format_for_prompt(contra),
        "count": len(lean),
        "updated_at": "local-regen",
    }
    json.dump(d, open(DATA, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"regen done: {len(lean)} 条 → data.json.active_contradictions")


if __name__ == "__main__":
    if "--explain" in sys.argv:
        explain()
    elif "--regen" in sys.argv:
        regen()
    else:
        contra = screen()
        if "--json" in sys.argv:
            print(json.dumps([{k: v for k, v in c.items() if k != "series"}
                              for c in contra], ensure_ascii=False))
