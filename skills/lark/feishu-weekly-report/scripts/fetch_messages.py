# -*- coding: utf-8 -*-
"""
Fetch Feishu (Lark) chat messages for a time range via lark-cli, then build digests
for weekly-report analysis.

Usage:
  python fetch_messages.py --start "2026-07-27T00:00:00+08:00" --end "2026-07-31T23:59:59+08:00" --outdir ./msgs

Outputs in outdir:
  chats.txt          chat_id|name list actually fetched
  oc_*.json          raw message arrays per chat
  digest.txt         per-chat digest (me / @me always kept; chats >100 msgs keyword-filtered)
  mine.txt           only my messages + messages @me (with chat headers) - READ THIS FIRST
  summary.txt        per-chat message counts
"""
import argparse, json, os, re, subprocess, sys

LARK_CLI = r"C:\Users\win10\.workbuddy\binaries\node\cli-connector-packages\lark-cli.cmd"

# chats to skip by name (bots / system / self)
SKIP_PATTERNS = ["助手", "机器人", "CLI", "Assistant", "OpenClaw", "汇报"]

KEYWORDS = ["发版","上线","测试","缺陷","bug","BUG","Bug","需求","评审","环境","数据","专项",
            "排期","会议","预发","生产","复测","用例","提测","流水线","重启","定时","蓝绿",
            "验证","报告","迁移","同步","接口","安全","自动化"]

def run(args):
    r = subprocess.run([LARK_CLI] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"ok": False, "err": (r.stderr or r.stdout)[:300]}

def get_me():
    d = run(["auth", "status", "--json", "--verify"])
    u = d.get("identities", {}).get("user", {})
    return u.get("openId", ""), u.get("userName", "")

def list_chats(max_pages):
    chats, token = [], None
    for _ in range(max_pages):
        args = ["im", "+chat-list", "--as", "user", "--types", "p2p,group",
                "--sort", "active_time", "--page-size", "80", "--format", "json"]
        if token:
            args += ["--page-token", token]
        d = run(args)
        if not d.get("ok"):
            break
        data = d.get("data", {})
        chats.extend(data.get("chats", []))
        if data.get("has_more") and data.get("page_token"):
            token = data["page_token"]
        else:
            break
    return chats

def fetch_chat(cid, start, end, max_pages=20):
    msgs, token = [], None
    for _ in range(max_pages):
        args = ["im", "+chat-messages-list", "--as", "user", "--chat-id", cid,
                "--start", start, "--end", end, "--order", "asc",
                "--page-size", "50", "--no-reactions", "--format", "json"]
        if token:
            args += ["--page-token", token]
        d = run(args)
        if not d.get("ok"):
            break
        data = d.get("data", {})
        msgs.extend(data.get("messages", []))
        if data.get("has_more") and data.get("page_token"):
            token = data["page_token"]
        else:
            break
    return msgs

def clean(text, limit=300):
    if not text:
        return ""
    t = re.sub(r"!\[Image\]\([^)]*\)", "[图]", text)
    t = re.sub(r"\[File\]\([^)]*\)", "[文件]", t)
    return t.replace("\n", " ").strip()[:limit]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help='ISO8601, e.g. "2026-07-27T00:00:00+08:00"')
    ap.add_argument("--end", required=True)
    ap.add_argument("--outdir", default="./msgs")
    ap.add_argument("--chat-pages", type=int, default=2, help="pages of chat list (80/page)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    os.chdir(args.outdir)

    me_id, me_name = get_me()
    if not me_id:
        print("ERROR: feishu user identity not ready; run: lark-cli auth status --json --verify")
        sys.exit(1)
    print(f"current user: {me_name} ({me_id})")

    chats = list_chats(args.chat_pages)
    fetched, summary = [], []
    for c in chats:
        name = c.get("name") or "(no name)"
        cid = c["chat_id"]
        if name == me_name or any(p in name for p in SKIP_PATTERNS):
            continue
        msgs = fetch_chat(cid, args.start, args.end)
        if not msgs:
            continue
        with open(f"{cid}.json", "w", encoding="utf-8") as f:
            json.dump(msgs, f, ensure_ascii=False)
        fetched.append((cid, name, len(msgs)))
        summary.append(f"{name}: {len(msgs)}")
        print(f"{name}: {len(msgs)} msgs", flush=True)

    with open("chats.txt", "w", encoding="utf-8") as f:
        for cid, name, _ in fetched:
            f.write(f"{cid}|{name}\n")
    with open("summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary))

    digest, mine = [], []
    for cid, name, total in fetched:
        msgs = json.load(open(f"{cid}.json", encoding="utf-8"))
        lines = []
        for m in msgs:
            s = m.get("sender", {})
            if s.get("sender_type") != "user":
                continue
            content = clean(m.get("content", ""))
            if not content:
                continue
            is_me = s.get("id") == me_id
            at_me = any(x.get("id") == me_id for x in m.get("mentions", []))
            kw = any(k in content for k in KEYWORDS)
            if total > 100 and not (is_me or at_me or kw):
                continue
            tag = " [★ME★]" if is_me else (" [@ME]" if at_me else "")
            line = f"{m.get('create_time','')} {s.get('name','?')}{tag}: {content}"
            lines.append(line)
            if is_me or at_me:
                mine.append(line)
        if lines:
            digest.append(f"\n{'='*70}\n会话: {name} (本周 {total} 条, 摘录 {len(lines)} 条)\n{'='*70}")
            digest.extend(lines)
            mine.append(f"----- 会话: {name} -----") if not any(isinstance(x, str) and x.startswith("-----") for x in mine[-1:]) else None

    # rebuild mine.txt grouped by chat
    mine_out = []
    for cid, name, total in fetched:
        msgs = json.load(open(f"{cid}.json", encoding="utf-8"))
        chat_lines = []
        for m in msgs:
            s = m.get("sender", {})
            if s.get("sender_type") != "user":
                continue
            is_me = s.get("id") == me_id
            at_me = any(x.get("id") == me_id for x in m.get("mentions", []))
            if not (is_me or at_me):
                continue
            content = clean(m.get("content", ""), 500)
            tag = "★ME★" if is_me else "@ME"
            chat_lines.append(f"{m.get('create_time','')} {s.get('name','?')} [{tag}]: {content}")
        if chat_lines:
            mine_out.append(f"\n===== 会话: {name} =====")
            mine_out.extend(chat_lines)

    with open("digest.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(digest))
    with open("mine.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(mine_out))
    print(f"\nDONE. chats={len(fetched)}, digest={len(digest)} lines, mine={len(mine_out)} lines")

if __name__ == "__main__":
    main()
