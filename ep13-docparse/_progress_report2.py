import json, glob, os, collections, datetime
d = r"D:/study/ai-jms/ep13-docparse/cells/ep13-full-001"
files = sorted(glob.glob(os.path.join(d, "*.json")))
rid = collections.Counter(); mt = []
for f in files:
    j = json.load(open(f, encoding="utf-8"))
    rid[j.get("run_id")] += 1
    st = os.stat(f)
    mt.append((st.st_mtime, os.path.basename(f), j.get("run_id"), j.get("set"), j.get("layer")))
print("run_id:", dict(rid))
mt.sort()
print("oldest:", datetime.datetime.fromtimestamp(mt[0][0]), mt[0][1])
print("newest:", datetime.datetime.fromtimestamp(mt[-1][0]), mt[-1][1])
# count per day
days = collections.Counter(datetime.datetime.fromtimestamp(t[0]).strftime("%m-%d %H") for t in mt)
print("by hour:", dict(sorted(days.items())))
# recent 10
for t in mt[-10:]:
    print("  ", datetime.datetime.fromtimestamp(t[0]).strftime("%m-%d %H:%M:%S"), t[1], t[2], t[3], t[4])
# sets/layers
sl = collections.Counter()
for f in files:
    j = json.load(open(f, encoding="utf-8"))
    sl[(j.get("set"), j.get("layer"))] += 1
print("set/layer:", dict(sl))
# manifest
m = json.load(open(r"D:/study/ai-jms/ep13-docparse/samples/manifest.json", encoding="utf-8"))
print("manifest keys:", list(m.keys()))
