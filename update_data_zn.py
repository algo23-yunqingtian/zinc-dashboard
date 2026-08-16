#!/usr/bin/env python3
"""
zinc dashboard data updater — runs locally on schedule.
Updates data.json in zinc_gh_static/ with fresh data from Zhiji + akshare + AI.
Also syncs to GitHub repo for GitHub Actions Pages.
"""
import subprocess
import sys
import os
from datetime import datetime

# Set up environment
SCRIPT_DIR = "/home/ubuntu/zinc_dashboard_gh"
VENV_PYTHON = "/home/ubuntu/unified_venv/bin/python3"
ENV_FILE = os.path.join(SCRIPT_DIR, ".env")

# Load .env
for line in open(ENV_FILE):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

OUTPUT = "/home/ubuntu/zinc_gh_static/data.json"
os.environ["OUTPUT"] = OUTPUT

log = lambda msg: print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def main():
    log("Starting zinc data update...")
    
    # Run fetch_zn.py with venv that has akshare
    cmd = [VENV_PYTHON, os.path.join(SCRIPT_DIR, "fetch_zn.py")]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=os.environ)
    
    if result.returncode != 0:
        log(f"FAILED: {result.stderr[:500]}")
        sys.exit(1)
    
    # Parse output
    output_lines = result.stdout.strip().split('\n')
    for line in output_lines:
        log(line)
    
    # Export news_cache.json from local DB (so GitHub Actions can read it)
    # 统一走 scorer_v2 重新打分（单一打分来源，不再依赖 DB 旧 tier）
    log("Exporting news_cache.json...")
    try:
        import sqlite3, json, re, urllib.parse
        import sys as _sys
        _sys.path.insert(0, SCRIPT_DIR)
        import scorer_v2_zn as scorer_v2
        conn = sqlite3.connect('/home/ubuntu/analysis/zinc_v1.db')
        c = conn.cursor()
        c.execute('SELECT date, content, tier, source FROM news_zinc_scored WHERE tier IN (?, ?) ORDER BY date DESC LIMIT 60', ('A', 'B'))
        news_items = []
        seen_titles = set()
        for date, content, tier, source in c.fetchall():
            m = re.search(r'【([^】]+)】', content)
            if m:
                title = m.group(1).replace('SHMET','').replace('上海金属网','').strip()[:80]
                body = content[m.end():].strip()[:200]
            else:
                title, body = content[:60], content[60:].strip()[:200]
            if not title or title == '快讯' or title in seen_titles:
                continue
            entry = scorer_v2.build_entry(title, body, source or 'SMM', date[:19],
                                          f"https://www.smm.cn/search/?keyword={urllib.parse.quote(title)}")
            if not entry['relevant']:
                continue
            seen_titles.add(title)
            news_items.append(entry)
        news_items.sort(key=lambda x: x['score'], reverse=True)
        news_items = news_items[:30]
        conn.close()
        cache_path = os.path.join(SCRIPT_DIR, 'news_cache.json')
        with open(cache_path, 'w') as f:
            json.dump(news_items, f, ensure_ascii=False)
        log(f"  exported {len(news_items)} news items (scorer v2)")
    except Exception as e:
        log(f"news_cache export failed: {e}")

    # Sync to GitHub repo
    log("Syncing data.json to GitHub repo...")
    import shutil
    gh_data = os.path.join(SCRIPT_DIR, "data.json")
    shutil.copy2(OUTPUT, gh_data)
    
    # Try git commit & push (non-blocking)
    try:
        subprocess.run(
            ["git", "add", "data.json"],
            cwd=SCRIPT_DIR, capture_output=True, timeout=10
        )
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=SCRIPT_DIR, capture_output=True, timeout=10
        )
        if diff.returncode != 0:  # has changes
            subprocess.run(
                ["git", "commit", "-m", f"update data {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                cwd=SCRIPT_DIR, capture_output=True, timeout=10,
                env={**os.environ, "GIT_AUTHOR_NAME": "zn-bot", "GIT_AUTHOR_EMAIL": "zn-bot@github.com",
                     "GIT_COMMITTER_NAME": "zn-bot", "GIT_COMMITTER_EMAIL": "zn-bot@github.com"}
            )
            # Push in background (don't block)
            subprocess.Popen(
                ["git", "push"],
                cwd=SCRIPT_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            log("Git push started in background")
        else:
            log("No data changes to commit")
    except Exception as e:
        log(f"Git sync skipped: {e}")
    
    log("Done!")

if __name__ == "__main__":
    main()
