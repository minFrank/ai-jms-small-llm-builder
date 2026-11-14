import json, glob, os, statistics, collections
base = r'D:/study/ai-jms/ep13-docparse'
man = json.load(open(os.path.join(base,'samples','manifest.json'), encoding='utf-8'))
sha_map = {s['sha256']: s['img'] for s in man['samples']}
uu_map = {s['sample_uuid']: s['img'] for s in man['samples']}
cells = glob.glob(os.path.join(base,'cells','ep13-full-001','*.json'))
neg = []; normal = []; per_eng = collections.defaultdict(list)
for f in cells:
    d = json.load(open(f, encoding='utf-8'))
    cer = d.get('cer_median')
    if cer is None or cer < 0:
        inp = d.get('input') or {}
        img = sha_map.get(inp.get('sha256')) or uu_map.get(inp.get('sample_uuid')) or '?'
        neg.append((d['engine'], img, cer, d['status']))
        continue
    per_eng[d['engine']].append(cer)
    if cer < 0.5: normal.append(cer)
normal.sort()
print('cer<0/None cells =', len(neg), neg)
print('normal(0<=cer<0.5) n=%d median=%.6f' % (len(normal), statistics.median(normal)))
for e in sorted(per_eng):
    v = sorted(per_eng[e])
    print('ENG', e, 'n=%d med=%.4f max=%.4f' % (len(v), statistics.median(v), v[-1]))
allc = [c for v in per_eng.values() for c in v]
print('all valid cer n=%d median=%.4f' % (len(allc), statistics.median(allc)))
