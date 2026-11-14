# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r"D:/study/ai-jms/ep13-docparse"
RUN  = "ep13-full-001"
CELLS = os.path.join(BASE, "cells", RUN)

man = json.load(open(os.path.join(BASE, "samples", "manifest.json"), encoding="utf-8"))
print("manifest keys:", list(man.keys()))
for k, v in man.items():
    if isinstance(v, list):
        print(k, "list len", len(v), "first:", json.dumps(v[0], ensure_ascii=False)[:400])
    elif isinstance(v, dict):
        print(k, "dict len", len(v), "first:", json.dumps(list(v.items())[0], ensure_ascii=False)[:400])
    else:
        print(k, "=", v)

files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
mt = [(os.path.getmtime(f), os.path.basename(f)) for f in files]
mt.sort()
print("\nfirst mtime:", datetime.datetime.fromtimestamp(mt[0][0]).isoformat(), mt[0][1])
print("last  mtime:", datetime.datetime.fromtimestamp(mt[-1][0]).isoformat(), mt[-1][1])

# rate: intervals between consecutive completions over last N
times = [t for t, _ in mt]
# overall
span = (times[-1] - times[0]) / 60.0
print("span first->last: %.1f min for %d cells -> %.3f min/cell" % (span, len(times), span/len(times)))
# last 10
if len(times) >= 11:
    span10 = (times[-1] - times[-11]) / 60.0
    print("last 10 intervals: %.1f min -> %.2f min/cell" % (span10, span10/10))
# last 20
if len(times) >= 21:
    span20 = (times[-1] - times[-21]) / 60.0
    print("last 20 intervals: %.1f min -> %.2f min/cell" % (span20, span20/20))

# map sample_id -> img via manifest (find list of samples)
samples = None
for k, v in man.items():
    if isinstance(v, list) and v and isinstance(v[0], dict):
        samples = v
        break
    if isinstance(v, dict) and v and isinstance(list(v.values())[0], dict):
        samples = list(v.values())[0] if False else v
smap = {}
if samples:
    if isinstance(samples, dict):
        for sid, item in samples.items():
            smap[sid] = item.get("img") or item.get("path") or item.get("file") or sid
    else:
        for item in samples:
            sid = item.get("sample_id") or item.get("id") or item.get("sha256")
            smap[sid] = item.get("img") or item.get("path") or item.get("file") or sid
print("\nsmap size:", len(smap), "sample:", list(smap.items())[:2])

# outlier list with sample names
cells = [json.load(open(f, encoding="utf-8")) for f in files]
out = []
for c in cells:
    cer = c.get("cer_median")
    if cer is not None and cer >= 0.5:
        sid = c.get("sample_id")
        out.append((cer, c.get("engine"), smap.get(sid, sid), c.get("set"), c.get("layer")))
out.sort(reverse=True)
print("\nOUTLIERS (cer>=0.5):")
for cer, eng, img, s, layer in out:
    print("  %.4f %s %s set=%s layer=%s" % (cer, eng, img, s, layer))

# normal median + per engine
import collections
per = collections.defaultdict(list)
allnorm = []
for c in cells:
    cer = c.get("cer_median")
    if cer is None: continue
    if cer < 0.5:
        allnorm.append(cer)
        per[c.get("engine")].append(cer)
print("\nnormal median: %.4f (n=%d)" % (statistics.median(allnorm), len(allnorm)))
for e, v in sorted(per.items()):
    print("  %s n=%d median=%.4f" % (e, len(v), statistics.median(v)))

# skip/fail mismatch: which cells in state
print("\nn_run+n_skip =", 102+5, "cell files =", len(files))
