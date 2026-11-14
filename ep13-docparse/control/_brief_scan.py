# -*- coding: utf-8 -*-
import json, os, glob, statistics, datetime, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(BASE, 'cells', 'ep13-full-001')
now = datetime.datetime.now()

bs = json.load(open(os.path.join(BASE, 'control', 'batch_state.json'), encoding='utf-8'))
print('BATCH_STATE:', json.dumps(bs, ensure_ascii=False))

files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
print('CELL_FILES:', len(files))

rows = []
for f in files:
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception as e:
        rows.append({'file': os.path.basename(f), 'status': 'PARSE_ERR', 'err': str(e)})
        continue
    rows.append({
        'file': os.path.basename(f),
        'status': d.get('status'),
        'engine': d.get('engine'),
        'cer': d.get('cer_median'),
        'wall': d.get('wall_median'),
        'sha': (d.get('input') or {}).get('sha256') if isinstance(d.get('input'), dict) else d.get('input_sha256') or (d.get('input') or {}).get('sha256') if isinstance(d.get('input'), dict) else None,
        'mtime': datetime.datetime.fromtimestamp(os.path.getmtime(f)),
    })

# status dist
from collections import Counter, defaultdict
print('STATUS_DIST:', dict(Counter(r['status'] for r in rows)))
eng_status = defaultdict(Counter)
for r in rows:
    eng_status[r.get('engine') or '?'][r['status']] += 1
for e in sorted(eng_status):
    print('  ENG', e, dict(eng_status[e]))

# non-complete
nonc = [r for r in rows if r['status'] != 'complete']
for r in nonc:
    print('NONCOMPLETE:', r['file'], r['status'], r.get('cer'), r.get('wall'), r.get('err'))

# CER stats among complete with numeric cer < 0.5
normal = [r for r in rows if r['status'] == 'complete' and isinstance(r['cer'], (int, float)) and r['cer'] < 0.5]
if normal:
    cers = sorted(r['cer'] for r in normal)
    med = statistics.median(cers)
    print('CER_NORMAL_N:', len(cers), 'MEDIAN: %.4f' % med)
out = [r for r in rows if isinstance(r['cer'], (int, float)) and r['cer'] >= 0.5]
# map sha -> sample img
try:
    man = json.load(open(os.path.join(BASE, 'samples', 'manifest.json'), encoding='utf-8'))
except Exception as e:
    man = None
    print('MANIFEST_ERR', e)
sha2img = {}
if man is not None:
    if isinstance(man, dict):
        items = man.get('samples') or man.get('items') or man
    else:
        items = man
    if isinstance(items, dict):
        for k, v in items.items():
            if isinstance(v, dict):
                sha2img[k] = v.get('img') or v.get('image') or v.get('path') or k
            else:
                sha2img[k] = v
    else:
        for v in items:
            if isinstance(v, dict):
                s = v.get('sha256') or (v.get('input') or {}).get('sha256')
                if s:
                    sha2img[s] = v.get('img') or v.get('image') or v.get('path') or s

for r in sorted(out, key=lambda x: -x['cer']):
    sha = r.get('sha')
    img = sha2img.get(sha, sha)
    if isinstance(img, str) and len(img) > 60:
        img = os.path.basename(img)
    print('OUTLIER: CER=%.3f eng=%s sample=%s' % (r['cer'], r['engine'], img))

# wall median among complete numeric
walls = [r['wall'] for r in rows if r['status'] == 'complete' and isinstance(r['wall'], (int, float))]
if walls:
    print('WALL_MEDIAN: %.1f  n=%d  min=%.1f max=%.1f' % (statistics.median(walls), len(walls), min(walls), max(walls)))

# recent mtimes for rate
mts = sorted(r['mtime'] for r in rows)
print('OLDEST_MTIME:', mts[0], 'NEWEST_MTIME:', mts[-1], 'NOW:', now)
print('AGE_NEWEST_MIN: %.1f' % ((now - mts[-1]).total_seconds() / 60))
