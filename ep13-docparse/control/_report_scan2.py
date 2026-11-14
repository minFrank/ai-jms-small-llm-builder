import json, os, collections, datetime, glob, statistics
base = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(base, "samples/manifest.json"), encoding="utf-8"))
print("SPEC:", json.dumps(man.get("spec"), ensure_ascii=False)[:1500])
print("COUNT:", man.get("count"))
s0 = man["samples"][0]
print("SAMPLE0:", json.dumps(s0, ensure_ascii=False)[:600])
sha2img = {}
for s in man["samples"]:
    sha2img[s.get("sha256") or s.get("input_sha256")] = s.get("img") or s.get("path") or s.get("file")
print("MAP_N:", len(sha2img))

files = sorted(glob.glob(os.path.join(base, "cells/ep13-full-001/*.json")))
rows = [json.load(open(f, encoding="utf-8")) for f in files]
print("R0:", json.dumps({k: rows[0][k] for k in ("cell_key","sample_id","input","engine","status","cer_median","wall_median")}, ensure_ascii=False))

started = datetime.datetime.fromisoformat(json.load(open(os.path.join(base,"control/batch_state.json"), encoding="utf-8"))["started_at"])
new_files = 0
for f in files:
    mt = datetime.datetime.fromtimestamp(os.path.getmtime(f))
    if mt >= started:
        new_files += 1
print("CELLS_WRITTEN_SINCE_START:", new_files, "of", len(files))

# outliers with names
out = []
for f, r in zip(files, rows):
    c = r.get("cer_median")
    if c is not None and c >= 0.5:
        sha = r.get("input")
        img = sha2img.get(sha, sha[:10] if sha else "?")
        out.append((c, r.get("engine"), r.get("sample_id"), img, os.path.basename(f)))
print("OUTLIERS:", len(out))
for c, e, sid, img, fn in sorted(out, key=lambda x: -x[0]):
    print("  %.4f | %s | %s | sample_id=%s | %s" % (c, e, img, sid, fn))

# per-engine stats
by = collections.defaultdict(list)
for r in rows:
    by[r.get("engine")].append(r)
for e, rs in sorted(by.items()):
    cs = sorted(x.get("cer_median") for x in rs if x.get("cer_median") is not None)
    ws = sorted(x.get("wall_median") for x in rs if x.get("wall_median") is not None)
    nrm = [c for c in cs if c < 0.5]
    print("ENG %-13s n=%d cer_med=%s normal_med=%s outlier=%d wall_med=%s" % (
        e, len(rs), round(statistics.median(cs),4) if cs else None,
        round(statistics.median(nrm),4) if nrm else None,
        sum(1 for c in cs if c >= 0.5), round(statistics.median(ws),1) if ws else None))

# samples present per engine
print("SAMPLES:", len(set(r.get("sample_id") for r in rows)))
missing = collections.Counter()
allsamp = [s.get("id") or s.get("img") for s in man["samples"]]
have = set(r.get("sample_id") for r in rows)
for e in set(r.get("engine") for r in rows):
    got = set(r.get("sample_id") for r in rows if r.get("engine")==e)
    miss = [s for s in allsamp if s not in got]
    if miss:
        print("MISSING", e, miss)
