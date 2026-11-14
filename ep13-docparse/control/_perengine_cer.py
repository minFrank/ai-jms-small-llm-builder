import json, glob, os, statistics, collections

CELLS = r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001"
files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
per = collections.defaultdict(list)
per_all = collections.defaultdict(list)
for p in files:
    d = json.load(open(p, encoding="utf-8"))
    if d.get("status") == "complete" and isinstance(d.get("cer_median"), (int, float)):
        per[d["engine"]].append(d["cer_median"])
        per_all[d["engine"]].append(d.get("wall_median"))
for e in sorted(per):
    v = sorted(per[e])
    w = [x for x in per_all[e] if isinstance(x, (int, float))]
    print("%-14s n=%2d cer_median=%s  n_out>=0.5=%d  wall_median=%s" % (
        e, len(v), round(statistics.median(v), 4),
        sum(1 for x in v if x >= 0.5),
        round(statistics.median(w), 2) if w else "-"))
