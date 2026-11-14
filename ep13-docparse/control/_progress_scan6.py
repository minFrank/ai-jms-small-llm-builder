import json, glob, os, datetime, collections

CELLS = r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001"
files = sorted(glob.glob(os.path.join(CELLS, "*.json")))
mt = sorted((os.path.getmtime(p), p) for p in files)

# session = cells after the 751.9 min gap (11-06 22:21)
cut = datetime.datetime(2026, 11, 6, 22, 20, 0).timestamp()
sess = [(t, p) for t, p in mt if t >= cut]
span = (sess[-1][0] - sess[0][0]) / 60.0
print("SESSION_N", len(sess), "SPAN_MIN", round(span, 1),
      "PER_CELL_MIN", round(span / max(len(sess) - 1, 1), 2),
      "from", datetime.datetime.fromtimestamp(sess[0][0]).strftime("%m-%d %H:%M:%S"),
      "to", datetime.datetime.fromtimestamp(sess[-1][0]).strftime("%m-%d %H:%M:%S"))
eng = collections.Counter()
for t, p in sess:
    d = json.load(open(p, encoding="utf-8"))
    eng[(d["engine"], d["status"])] += 1
print("SESSION_ENGINES", dict(eng))

# completed-only rate within session (exclude instant-fail oxr)
comp = [(t, p) for t, p in sess if json.load(open(p, encoding="utf-8"))["status"] == "complete"]
if len(comp) >= 2:
    s2 = (comp[-1][0] - comp[0][0]) / 60.0
    print("SESSION_COMPLETE_N", len(comp), "SPAN_MIN", round(s2, 1),
          "PER_CELL_MIN", round(s2 / (len(comp) - 1), 2))

# oxr fail spacing (time per failed cell)
oxr = [(t, p) for t, p in sess if "__oxr__" in p]
if len(oxr) >= 2:
    s3 = (oxr[-1][0] - oxr[0][0]) / 60.0
    print("SESSION_OXR_N", len(oxr), "SPAN_MIN", round(s3, 1),
          "PER_CELL_MIN", round(s3 / (len(oxr) - 1), 2))

# monkey-only final session rate
mon = [(t, p) for t, p in sess if "__monkey_rec__" in p]
if len(mon) >= 2:
    s4 = (mon[-1][0] - mon[0][0]) / 60.0
    print("SESSION_MONKEY_N", len(mon), "SPAN_MIN", round(s4, 1),
          "PER_CELL_MIN", round(s4 / (len(mon) - 1), 2))

# whole-run elapsed vs cells
print("RUN_FIRST", datetime.datetime.fromtimestamp(mt[0][0]).strftime("%m-%d %H:%M"),
      "RUN_LAST", datetime.datetime.fromtimestamp(mt[-1][0]).strftime("%m-%d %H:%M"),
      "CELLS", len(mt))
