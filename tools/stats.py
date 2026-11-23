"""Pull metrics for all sent posts (TikTok + X) since a date and write stats.csv. usage: stats.py SINCE_ISO OUT.csv"""
import json, subprocess, sys, csv
since, out = sys.argv[1:3]
q = ('query{posts(first:100,input:{organizationId:"6afac0182fbcba384e4540d0",filter:{channelIds:["6afac1e7ece6dfde5fe16b6a","6b03121f8541f09ecb65a5cc"],status:[sent]}})'
     '{edges{node{sentAt channelService text externalLink metricsUpdatedAt assets{... on VideoAsset{source}} metrics{name value}}}}}')
r = subprocess.run(["curl", "-sS", "https://api.buffer.com", "-H", "Authorization: Bearer proxy-injected", "-H", "Content-Type: application/json",
                    "-d", json.dumps({"query": q})], capture_output=True, text=True).stdout
rows = []
for e in json.loads(r)["data"]["posts"]["edges"]:
    n = e["node"]
    if (n["sentAt"] or "") < since: continue
    m = {x["name"]: x["value"] for x in n["metrics"] or []}
    src = (n["assets"] or [{}])[0].get("source", "").split("affectionate-hawking-iom3sr/")[-1]
    rows.append(dict(sent=n["sentAt"][:16], ch=n["channelService"], file=src, views=m.get("Video Views", m.get("Views", m.get("Impressions"))),
                     avg_watch=m.get("Avg. Watch Time (sec)"), likes=m.get("Reactions"), comments=m.get("Comments"), shares=m.get("Shares", m.get("Reposts")),
                     updated=(n["metricsUpdatedAt"] or "")[:16], text=(n["text"] or "")[:60], link=n["externalLink"]))
rows.sort(key=lambda x: x["sent"])
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
for x in rows: print(x["sent"], x["ch"][:2], x["file"][:28].ljust(28), x["views"], x["avg_watch"], x["likes"], x["shares"], "upd", x["updated"][5:])
