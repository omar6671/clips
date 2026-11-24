"""Keep the Buffer queue filled from a weekly plan (Buffer plan allows 10 scheduled posts per channel).
usage: topup.py PLAN.json [--dry]
PLAN: [{"due": "2026-11-23T16:00", "path": "week1/pod_p2.mp4", "tt": "caption file", "x": "caption file"}, ...]
Each item is sent to TikTok + X. Items already scheduled/sent are recorded in PLAN.state.json and never sent twice;
items whose time has passed are skipped. Video must already be pushed to the branch (raw URL)."""
import json, os, subprocess, sys, datetime

BRANCH = "claude/affectionate-hawking-iom3sr"
RAW = f"https://raw.githubusercontent.com/omar6671/clips/{BRANCH}/"
CH = {"tt": ("6afac1e7ece6dfde5fe16b6a", "tiktok"), "x": ("6b03121f8541f09ecb65a5cc", "twitter"), "ig": ("6b05df788541f09ecb8f0853", "instagram")}
LIMIT = 10
plan_p = sys.argv[1]; dry = "--dry" in sys.argv
base = os.path.dirname(os.path.abspath(plan_p))
plan = json.load(open(plan_p, encoding="utf-8"))
state_p = plan_p.replace(".json", ".state.json")
state = json.load(open(state_p)) if os.path.exists(state_p) else {}


def gql(q):
    r = subprocess.run(["curl", "-sS", "--max-time", "60", "https://api.buffer.com", "-H", "Authorization: Bearer proxy-injected",
                        "-H", "Content-Type: application/json", "-d", json.dumps({"query": q})], capture_output=True, text=True)
    return json.loads(r.stdout)


ids = ",".join('"%s"' % c for c, _ in CH.values())
d = gql('query{posts(first:100,input:{organizationId:"6afac0182fbcba384e4540d0",filter:{channelIds:[%s],status:[scheduled]}}){edges{node{channelId}}}}' % ids)
count = {k: 0 for k in CH}
for e in d["data"]["posts"]["edges"]:
    for k, (cid, _) in CH.items():
        if e["node"]["channelId"] == cid: count[k] += 1
now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
for it in sorted(plan, key=lambda x: x["due"]):
    if it["due"] <= now: continue
    if not os.path.exists(os.path.join("/home/user/clips", it["path"])):
        print("not ready (skipped, later items wait):", it["path"]); break
    for k, (cid, svc) in CH.items():
        if k not in it: continue
        key = f'{it["due"]}|{it["path"]}|{k}'
        if state.get(key): continue
        if count[k] >= LIMIT: continue
        if dry: print("would schedule", key); continue
        r = subprocess.run(["python3", "/home/user/clips/tools/buffer_post.py", cid, svc, RAW + it["path"], it["due"] + ":00Z",
                            os.path.join(base, it[k])], capture_output=True, text=True).stdout
        ok = '"status":"scheduled"' in r
        print(key, "OK" if ok else r.strip()[:200])
        if ok:
            state[key] = True; count[k] += 1
            open(os.path.join(base, "log.txt"), "a").write(f'{it["due"]}Z {it["path"]} {svc} scheduled (topup)\n')
    if all(count[k] >= LIMIT for k in ("tt", "x")): break
json.dump(state, open(state_p, "w"), indent=0)
print("queue:", count)
