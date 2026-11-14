# -*- coding: utf-8 -*-
import json, glob, os, statistics, datetime, collections

fs = sorted(glob.glob("D:/study/ai-jms/ep13-docparse/cells/ep13-full-001/*.json"))
mt = [(os.path.getmtime(f), f) for f in fs]
mt.sort()
t0, f0 = mt[0]
print("oldest cell mtime:", datetime.datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"), os.path.basename(f0))
print("newest cell mtime:", datetime.datetime.fromtimestamp(mt[-1][0]).strftime("%Y-%m-%d %H:%M:%S"), os.path.basename(mt[-1][1]))

now = datetime.datetime.now().timestamp()
span_h = (now - t0) / 3600.0
print("span since first cell: %.2f h, cells=%d, avg=%.2f min/cell" % (span_h, len(fs), span_h*60/len(fs)))

# cells per hour bucket
b = collections.Counter()
for t, f in mt:
    b[datetime.datetime.fromtimestamp(t).strftime("%m-%d %H")] += 1
for k in sorted(b):
    print("   ", k, b[k])

# per-cell duration estimate = n_attempt * wall_median ; also sum reps durations if present
per_eng = collections.defaultdict(list)
durs = []
for f in fs:
    d = json.load(open(f, encoding="utf-8"))
    eng = d.get("engine")
    na = d.get("n_attempt") or 0
    wm = d.get("wall_median") or 0
    est = na * wm
    reps = d.get("reps") or []
    rep_sum = 0.0
    for r in reps:
        if isinstance(r, dict):
            w = r.get("wall") or r.get("wall_s") or r.get("dur")
            if isinstance(w, (int, float)):
                rep_sum += w
    per_eng[eng].append(est if est else None)
    durs.append(est)
    if len(fs) and f == fs[0]:
        print("sample rep keys:", list(reps[0].keys()) if reps and isinstance(reps[0], dict) else reps[:2])
print("cell duration est (n_attempt*wall_median): median=%.1fs (%.1f min), n=%d" %
      (statistics.median(durs), statistics.median(durs)/60, len(durs)))
for k in sorted(per_eng):
    v = [x for x in per_eng[k] if x]
    if v:
        print("   %-14s n=%d median_dur=%.0fs (%.1f min)" % (k, len(v), statistics.median(v), statistics.median(v)/60))

# engines present / missing vs 26
cnt = collections.Counter(json.load(open(f, encoding="utf-8")).get("engine") for f in fs)
print("engine counts:", dict(cnt), " total:", sum(cnt.values()), " remaining to 130:", 130 - sum(cnt.values()))
print("missing per engine:", {k: 26 - v for k, v in cnt.items() if v < 26})
