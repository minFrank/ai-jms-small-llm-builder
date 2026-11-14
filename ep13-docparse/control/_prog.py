# -*- coding: utf-8 -*-
import json, os, glob, statistics, collections, datetime

BASE = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(BASE, 'cells', 'ep13-full-001')

st = json.load(open(os.path.join(BASE, 'control', 'batch_state.json'), encoding='utf-8'))
man = json.load(open(os.path.join(BASE, 'samples', 'manifest.json'), encoding='utf-8'))

# manifest: sha256 -> img  (may be dict of sha->name or list)
sha2img = {}
if isinstance(man, dict):
    for k, v in man.items():
        if isinstance(v, str):
            sha2img[k] = v
        elif isinstance(v, dict):
            sha2img[k] = v.get('img') or v.get('name') or v.get('file') or str(v)
elif isinstance(man, list):
    for v in man:
        sha2img[v.get('sha256')] = v.get('img') or v.get('name')

rows = []
for p in sorted(glob.glob(os.path.join(CELLS, '*.json'))):
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception as e:
        rows.append({'file': os.path.basename(p), 'status': 'PARSE_ERR', 'engine': '?', 'err': str(e)})
        continue
    inp = d.get('input') or {}
    sha = inp.get('sha256') or d.get('input_sha256')
    rows.append({
        'file': os.path.basename(p),
        'status': d.get('status'),
        'engine': d.get('engine') or d.get('eng') or '?',
        'cer': d.get('cer_median'),
        'wall': d.get('wall_median'),
        'sha': sha,
        'sample': d.get('sample') or d.get('img') or d.get('name'),
        'keys': sorted(d.keys()),
    })

print('=== batch_state ===')
print(json.dumps(st, ensure_ascii=False, indent=1))
print('total cell files:', len(rows))

# status distribution
by_status = collections.Counter(r['status'] for r in rows)
print('status dist:', dict(by_status))

# engine x status
eng_status = collections.defaultdict(collections.Counter)
for r in rows:
    eng_status[r['engine']][r['status']] += 1
print('engine x status:')
for e in sorted(eng_status):
    print('  %-14s %s' % (e, dict(eng_status[e])))

# non-complete
nonc = [r for r in rows if r['status'] != 'complete']
print('non-complete count:', len(nonc))
for r in nonc:
    print('   ', r['file'], r['status'], r.get('cer'), r.get('wall'))

# CER
cerc = [r for r in rows if isinstance(r.get('cer'), (int, float)) and r['cer'] < 0.5]
cers = sorted(r['cer'] for r in cerc)
med = statistics.median(cers) if cers else None
print('CER normal(<0.5) n=%d median=%.4f' % (len(cers), med) if cers else 'no cer')

out = [r for r in rows if isinstance(r.get('cer'), (int, float)) and r['cer'] >= 0.5]
out.sort(key=lambda r: -r['cer'])
print('CER outliers(>=0.5): %d' % len(out))
for r in out:
    name = r.get('sample')
    if not name and r.get('sha'):
        name = sha2img.get(r['sha'], r['sha'][:8])
    print('   cer=%.4f engine=%s sample=%s file=%s' % (r['cer'], r['engine'], name, r['file']))

walls = sorted(r['wall'] for r in rows if isinstance(r.get('wall'), (int, float)))
if walls:
    print('wall median=%.1fs n=%d  min=%.1f max=%.1f' % (statistics.median(walls), len(walls), walls[0], walls[-1]))

# rate: newest cell mtimes
mt = []
for p in glob.glob(os.path.join(CELLS, '*.json')):
    mt.append((os.path.getmtime(p), os.path.basename(p)))
mt.sort()
now = datetime.datetime.now().timestamp()
recent = [(t, f) for t, f in mt if now - t < 6 * 3600]
print('cells written last 6h:', len(recent))
for t, f in recent:
    print('   ', datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S'), f)

# non-complete & sample of keys
if rows:
    print('sample keys:', rows[0].get('keys'))
