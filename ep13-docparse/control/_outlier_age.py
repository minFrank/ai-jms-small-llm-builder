import json, glob, os, datetime, collections

CELLS = r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001"
CUT = datetime.datetime(2026, 11, 6, 22, 20, 0).timestamp()
rows = []
for p in sorted(glob.glob(os.path.join(CELLS, "*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    cer = d.get("cer_median")
    if d.get("status") == "complete" and isinstance(cer, (int, float)) and cer >= 0.5:
        t = os.path.getmtime(p)
        rows.append((cer, d["engine"], d.get("sample_id", "")[:8], d.get("set"),
                     datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M"),
                     t >= CUT))
rows.sort(reverse=True)
print("OUTLIERS n=%d  (session-new flag = mtime >= 11-06 22:20)" % len(rows))
for cer, eng, sid, st, ts, new in rows:
    print("  %.4f  %-12s %s  set=%s  mtime=%s %s" % (cer, eng, sid, st, ts, "NEW_THIS_BATCH" if new else ""))

# per-engine counts incl. session-new
c = collections.Counter((e, bool(n)) for _, e, _, _, _, n in rows)
print(dict(c))
