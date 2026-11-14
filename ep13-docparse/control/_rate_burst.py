import os, glob, datetime, collections, statistics

base = r"D:/study/ai-jms/ep13-docparse"
files = glob.glob(os.path.join(base, "cells", "ep13-full-001", "*.json"))
mts = sorted((os.path.getmtime(f), f) for f in files)
now = datetime.datetime.now()
print("NOW", now.isoformat(timespec="seconds"))
print("oldest cell:", datetime.datetime.fromtimestamp(mts[0][0]).strftime("%m-%d %H:%M:%S"),
      "newest:", datetime.datetime.fromtimestamp(mts[-1][0]).strftime("%m-%d %H:%M:%S"))
print("age newest cell (min): %.1f" % ((now.timestamp() - mts[-1][0]) / 60))

# hourly histogram of cell writes
hist = collections.Counter()
for t, f in mts:
    hist[datetime.datetime.fromtimestamp(t).strftime("%m-%d %H")] += 1
for k in sorted(hist):
    print("  ", k, hist[k])

# last batch window: cells written in the final contiguous burst before 01:27
final = [t for t, f in mts if t <= mts[-1][0]]
# find start: last gap > 20 min
start = final[-1]
for i in range(len(final) - 1, 0, -1):
    if final[i] - final[i - 1] > 20 * 60:
        start = final[i - 1]
        break
else:
    start = final[0]
n = sum(1 for t in final if t >= start)
span_min = (final[-1] - start) / 60
print("last burst: n=%d span=%.1f min rate=%.2f min/cell  window %s -> %s" % (
    n, span_min, span_min / n if n else 0,
    datetime.datetime.fromtimestamp(start).strftime("%H:%M:%S"),
    datetime.datetime.fromtimestamp(final[-1]).strftime("%H:%M:%S")))
