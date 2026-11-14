import json, glob, statistics, os, datetime
from collections import defaultdict, Counter

B = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(B + "/samples/manifest.json", encoding="utf-8"))
sha2img = {s["sha256"]: s["img"] for s in man["samples"]}
sha2id = {s["sha256"]: s["sample_id"] for s in man["samples"]}

recs = []
for f in glob.glob(B + "/cells/ep13-full-001/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    d["_f"] = os.path.basename(f)
    recs.append(d)

def g(d, *k):
    for x in k:
        if x in d and d[x] is not None:
            return d[x]
    return None

# sanity: what keys exist
print("KEYS", sorted({k for d in recs for k in d if not k.startswith('_')}))

out = []
by_sample = defaultdict(list)
for d in recs:
    cer = g(d, "cer_median", "cer")
    sha = g(d, "input_sha256", "input", "sha256")
    if isinstance(sha, dict):
        sha = sha.get("sha256")
    img = sha2img.get(sha, "?")
    sid = sha2id.get(sha, str(sha)[:12] if sha else "?")
    eng = g(d, "engine", "?")
    by_sample[sid].append((eng, cer))
    if isinstance(cer, (int, float)) and cer >= 0.5:
        out.append((cer, eng, sid, img))

print("OUTLIERS by sample:")
for sid, lst in sorted(by_sample.items()):
    o = [x for x in lst if isinstance(x[1], (int, float)) and x[1] >= 0.5]
    if o:
        allc = [x[1] for x in lst if isinstance(x[1], (int, float))]
        print("  %s n=%d/%d max=%.3f med=%.3f" % (sid, len(o), len(lst), max(allc), statistics.median(allc)),
              "eng:", ",".join("%s=%.2f" % (e, c) for e, c in sorted(o, key=lambda t: -t[1])))

# per engine CER stats
print("PER-ENGINE")
byeng = defaultdict(list)
for d in recs:
    cer = g(d, "cer_median", "cer")
    if isinstance(cer, (int, float)):
        byeng[g(d, "engine", "?")].append(cer)
for e, v in sorted(byeng.items()):
    print("  %-14s n=%d med=%.4f p25=%.4f p75=%.4f  <0.5=%d  >=0.5=%d" % (
        e, len(v), statistics.median(v), sorted(v)[len(v)//4], sorted(v)[(3*len(v))//4],
        sum(1 for c in v if c < 0.5), sum(1 for c in v if c >= 0.5)))

# wall per engine
print("WALL per engine")
byw = defaultdict(list)
for d in recs:
    w = g(d, "wall_median", "wall")
    if isinstance(w, (int, float)):
        byw[g(d, "engine", "?")].append(w)
for e, v in sorted(byw.items()):
    print("  %-14s med=%.1fs sum=%.0f min=%.1f max=%.1f" % (e, statistics.median(v), sum(v), min(v), max(v)))

print("WALL_ALL med=%.1f mean=%.1f n=%d" % (
    statistics.median([g(d,'wall_median','wall') for d in recs if isinstance(g(d,'wall_median','wall'),(int,float))]),
    statistics.mean([g(d,'wall_median','wall') for d in recs if isinstance(g(d,'wall_median','wall'),(int,float))]),
    len([d for d in recs if isinstance(g(d,'wall_median','wall'),(int,float))])))

norm = sorted(c for c in [g(d,'cer_median','cer') for d in recs] if isinstance(c,(int,float)) and c < 0.5)
print("CER normal(<0.5): n=%d med=%.4f" % (len(norm), statistics.median(norm)))
print("CER all: n=%d med=%.4f" % (len([g(d,'cer_median','cer') for d in recs if isinstance(g(d,'cer_median','cer'),(int,float))]),
      statistics.median([g(d,'cer_median','cer') for d in recs if isinstance(g(d,'cer_median','cer'),(int,float))])))
print("OUT_TOTAL", len(out))
