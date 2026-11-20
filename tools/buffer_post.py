"""Create one scheduled Buffer post. usage: buffer_post.py CHANNEL_ID tiktok|instagram VIDEO_URL DUE_ISO CAPTION_FILE"""
import json, sys, subprocess
ch, svc, url, due, capf = sys.argv[1:6]
text = open(capf, encoding="utf-8").read().strip()
inp = {"channelId": ch, "text": text, "schedulingType": "automatic", "mode": ("shareNow" if due == "now" else "customScheduled"),
       "needsApproval": False, "assets": [{"video": {"url": url}}]}
if svc == "instagram":
    inp["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}
if due != "now":
    inp["dueAt"] = due
q = """mutation($input: CreatePostInput!) { createPost(input: $input) {
  __typename ... on PostActionSuccess { post { id dueAt status } } ... on MutationError { message } } }"""
body = json.dumps({"query": q, "variables": {"input": inp}}, ensure_ascii=False)
r = subprocess.run(["curl", "-sS", "--max-time", "60", "https://api.buffer.com", "-H", "Authorization: Bearer proxy-injected",
                    "-H", "Content-Type: application/json", "--data-binary", "@-"], input=body.encode(), capture_output=True)
print(r.stdout.decode(), r.stderr.decode())
