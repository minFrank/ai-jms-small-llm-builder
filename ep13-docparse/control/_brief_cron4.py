import json, glob, os, collections

BASE = r"D:/study/ai-jms/ep13-docparse"
man = json.load(open(os.path.join(BASE, "samples/manifest.json"), encoding="utf-8"))
muuids = {s["sample_uuid"] for s in man["samples"]}
msid = {s["sample_id"] for s in man["samples"]}
print("manifest count:", man.get("count"), "uuids:", len(muuids), "sids:", len(msid))

rows = []
for f in sorted(glob.glob(os.path.join(BASE, "cells/ep13-full-001/*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    d["_f"] = os.path.basename(f)
    d["_uid"] = d["_f"].split("__")[0]
    rows.append(d)

# uuid -> cells
u2c = collections.defaultdict(list)
for r in rows:
    u2c[r["_uid"]].append(r)
print("distinct uuids in cells:", len(u2c))
notman = [u for u in u2c if u not in muuids]
print("uuid not in manifest:", notman)
for u in notman:
    for r in u2c[u]:
        print("   ", r["_f"], "sample_id=", r.get("sample_id"), "set=", r.get("set"), "status=", r.get("status"), "engine=", r.get("engine"))

# sample_id -> uuids in cells
s2u = collections.defaultdict(set)
for r in rows:
    s2u[r.get("sample_id")].add(r["_uid"])
dup = {k: v for k, v in s2u.items() if len(v) > 1}
print("sample_ids with >1 uuid:", dup)
print("cell sample_ids not in manifest sids:", [k for k in s2u if k not in msid])

# uuid with <5 cells
for u, cs in sorted(u2c.items()):
    if len(cs) != 5:
        print("uuid with %d cells:" % len(cs), u, [c["engine"] for c in cs])

# sid of full-001 cells: which sids present
print("sids in cells:", sorted(s2u))
