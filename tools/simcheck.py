"""Flag phrases a script shares with competitor transcripts (work/ref/r*.tr.json). usage: simcheck.py scripts.json [...]
Reports shared 3-word sequences (after light normalisation) per script/reference."""
import json, re, sys, glob
def norm(t):
    t = re.sub(r"[ً-ْـ]", "", t); t = re.sub(r"[إأآ]", "ا", t); t = t.replace("ة", "ه").replace("ى", "ي")
    return re.findall(r"[\w%]+", t.lower())
refs = {f.split("/")[-1][:3]: norm(" ".join(s[2] for s in json.load(open(f)))) for f in glob.glob("/home/user/work/ref/r*.tr.json")}
ng = lambda w, n: {" ".join(w[i:i+n]) for i in range(len(w)-n+1)}
COMMON = {"في مودرن وارفير", "مودرن وارفير فور", "مودرن وارفير 4", "كول اوف ديوتي"}
bad = 0
for p in sys.argv[1:]:
    for k, v in json.load(open(p)).items():
        w = norm(v[1]); g = ng(w, 3) - COMMON
        for r, rw in refs.items():
            hit = g & ng(rw, 3)
            if hit: bad += 1; print(f"{p.split('/')[-2]}/{k} ~ {r}: {sorted(hit)}")
print("FLAGGED" if bad else "CLEAN")
