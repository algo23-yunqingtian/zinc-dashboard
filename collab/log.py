#!/usr/bin/env python3
"""collab/log.py — 双 agent 共享笔记本读写助手（GitHub Contents API，无需 git CLI）

双方 agent 都用它追加/读取 collab/notebook.md：
  python collab/log.py add --agent CODEBUDDY --action modify \
      --target "fetch_zn.py:fetch_news" --desc "..." [--note "..."]
  python collab/log.py tail --n 20
  python collab/log.py read

认证：环境变量 GITHUB_TOKEN（不要硬编码进文件，也不要贴进聊天）。
冲突处理：并发追加时若 base sha 过期（HTTP 409），自动重新拉取并合并重试。
"""
import os
import sys
import json
import base64
import argparse
import datetime
import urllib.request
import urllib.error

REPO = "algo23-yunqingtian/zinc-dashboard"
PATH = "collab/notebook.md"
API = f"https://api.github.com/repos/{REPO}/contents/{PATH}"


def _token():
    t = os.environ.get("GITHUB_TOKEN")
    if not t:
        sys.exit("ERROR: 先设置环境变量 GITHUB_TOKEN 再运行（切勿硬编码或贴进聊天）")
    return t


def _branch(token):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}",
        headers={"Authorization": "token " + token, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["default_branch"]


def _api(method, url, token, data=None):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "token " + token)
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(req, timeout=30)


def get_file(token):
    try:
        with _api("GET", API, token) as r:
            d = json.load(r)
        return base64.b64decode(d["content"]).decode("utf-8"), d["sha"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        raise


def now_cst():
    tz = datetime.timezone(datetime.timedelta(hours=8))
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")


def add_entry(token, agent, action, target, desc, note):
    branch = _branch(token)
    block = (
        f"\n### [{now_cst()}] {agent} · {action.upper()}\n"
        f"- target: {target}\n"
        f"- desc: {desc}\n"
    )
    if note:
        block += f"- note: {note}\n"

    for _ in range(5):
        content, sha = get_file(token)
        new_content = (content or "") + block
        payload = {
            "message": f"notebook: {agent} {action} {target}",
            "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        try:
            with _api("PUT", API, token, json.dumps(payload).encode("utf-8")) as r:
                print("OK 已追加条目:", r.status)
            return
        except urllib.error.HTTPError as e:
            if e.code == 409:  # 其他人/agent 刚改过，重新拉取再合并
                continue
            raise
    print("FAILED 重试 5 次仍冲突，请稍后重试")


def tail(token, n=20):
    content, _ = get_file(token)
    if not content:
        print("(笔记本为空)")
        return
    parts = content.split("\n### [")
    head = parts[0]
    entries = ["### [" + p for p in parts[1:]]
    print(head)
    for e in entries[-n:]:
        print(e)


def main():
    p = argparse.ArgumentParser(description="双 agent 共享笔记本助手")
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add", help="追加一条变更记录")
    pa.add_argument("--agent", required=True, help="agent 名，如 CODEBUDDY / HERMES")
    pa.add_argument("--action", required=True, choices=["add", "remove", "modify"])
    pa.add_argument("--target", required=True, help="文件:函数 或 文件")
    pa.add_argument("--desc", required=True, help="功能说明")
    pa.add_argument("--note", default="", help="自由沟通内容")
    pt = sub.add_parser("tail", help="查看最近 n 条")
    pt.add_argument("--n", type=int, default=20)
    sub.add_parser("read", help="查看全部")
    args = p.parse_args()

    tok = _token()
    if args.cmd == "add":
        add_entry(tok, args.agent, args.action, args.target, args.desc, args.note)
    elif args.cmd == "tail":
        tail(tok, args.n)
    elif args.cmd == "read":
        tail(tok, 10 ** 9)


if __name__ == "__main__":
    main()
