import json, glob, os, statistics, collections, datetime

base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples/manifest.json"), encoding="utf-8"))
sha2name = {}
for s in man["samples"]:
    sha2name[s["sha256"]] = (s["sample_id"], s.get("img"), s.get("category"), s.get("kind"))
print("manifest samples:", len(man["samples"]))

files = sorted(glob.glob(os.path.join(base, "cells/ep13-full-001/*.json")))
rows = [json.load(open(p, encoding="utf-8")) for p in files]

# per-engine per-sample table for outliers
out = []
ts_all = []
for d in rows:
    cer = d.get("cer_median")
    sha = d.get("input", {}).get("sha256")
    name = sha2name.get(sha, ("?", "?", "?", "?"))
    # timestamps
    for r in d.get("reps", []):
        if r.get("ts"):
            ts_all.append(r["ts"])
    if cer is not None and cer >= 0.5:
        out.append((cer, d["engine"], name[0], name[1], name[2], d.get("cell_key")))

print("outliers >=0.5:", len(out))
# group by sample
bysample = collections.defaultdict(list)
for cer, eng, sid, img, cat, ck in out:
    bysample[sid].append((eng, cer, img, cat))
for sid, v in sorted(bysample.items(), key=lambda x: -max(c for _, c, _, _ in x[1])):
    v.sort(key=lambda x: -x[1])
    print("  sample=%s img=%s cat=%s -> n=%d | %s" % (
        sid, v[0][2], v[0][3], len(v),
        ", ".join("%s=%.3f" % (e, c) for e, c, _, _ in v)))

# known outliers check
known = [("xiaomi_vl", "shot_01", 0.71), ("xiaomi_vl", "table_01", 0.59)]
print("known check:")
for eng, sid, exp in known:
    hit = [(c, e) for c, e, s, i, ct, ck in out if s == sid and e == eng]
    print("   %s x %s -> %s (expect ~%.2f)" % (eng, sid, hit, exp))

# ts range
ts_all.sort()
print("rep ts range:", ts_all[0], "->", ts_all[-1], "n=", len(ts_all))
t0 = datetime.datetime.fromisoformat(ts_all[0])
t1 = datetime.datetime.fromisoformat(ts_all[-1])
hours = (t1 - t0).total_seconds() / 3600
print("elapsed hours=%.2f, cells=%d, min/cell=%.2f" % (hours, len(files), hours * 60 / len(files)))

# last cell completion (max ts)
print("last_progress vs now")

# per-engine CER normal medians
eng_cer = collections.defaultdict(list)
for d in rows:
    c = d.get("cer_median")
    if c is not None and c < 0.5:
        eng_cer[d["engine"]].append(c)
for e in sorted(eng_cer):
    print("   CER<0.5 %s n=%d median=%.4f" % (e, len(eng_cer[e]), statistics.median(eng_cer[e])))

# unstable / err fields
un = [d["cell_key"] for d in rows if d.get("unstable")]
ek = collections.Counter(d.get("err_kind") for d in rows if d.get("err_kind"))
print("unstable:", len(un), un[:10])
print("err_kind:", dict(ek))
print("n_fail sum:", sum(d.get("n_fail") or 0 for d in rows), "n_valid sum:", sum(d.get("n_valid") or 0 for d in rows), "n_attempt sum:", sum(d.get("n_attempt") or 0 for d in rows))
