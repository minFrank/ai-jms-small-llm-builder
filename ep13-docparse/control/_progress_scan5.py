import json, glob, os, datetime, collections

CELLS = r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001"
files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
mt = sorted((os.path.getmtime(p), p) for p in files)

# gap analysis to find sessions
prev = None
print("=== gaps > 20 min ===")
for t, p in mt:
    if prev is not None and (t - prev) / 60.0 > 20:
        print("GAP", round((t - prev) / 60.0, 1), "min before",
              datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M"),
              "|", os.path.basename(p)[:40])
    prev = t

# cells written on 11-07 (final session)
print("=== cells mtime on 11-07 ===")
c7 = [(t, p) for t, p in mt if datetime.datetime.fromtimestamp(t).strftime("%m-%d") == "11-07"]
print("N_1107", len(c7))
eng = collections.Counter()
for t, p in c7:
    d = json.load(open(p, encoding="utf-8"))
    eng[(d["engine"], d["status"])] += 1
print("ENGINES_1107", dict(eng))
if c7:
    span = (c7[-1][0] - c7[0][0]) / 60.0
    print("SPAN_1107_MIN", round(span, 1), "PER_CELL", round(span / max(len(c7) - 1, 1), 2),
          "from", datetime.datetime.fromtimestamp(c7[0][0]).strftime("%H:%M:%S"),
          "to", datetime.datetime.fromtimestamp(c7[-1][0]).strftime("%H:%M:%S"))

# per-day counts
day = collections.Counter()
for t, p in mt:
    day[datetime.datetime.fromtimestamp(t).strftime("%m-%d")] += 1
print("PER_DAY", dict(sorted(day.items())))

# monkey_rec only mtimes (to identify n_run=12)
mon = [(t, p) for t, p in mt if "__monkey_rec__" in p]
print("MONKEY_LAST12_SPAN_MIN", round((mon[-1][0] - mon[-12][0]) / 60.0, 1) if len(mon) >= 12 else None)
print("MONKEY_MTIMES")
for t, p in mon[-14:]:
    print("  ", datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M:%S"), os.path.basename(p)[:30])
