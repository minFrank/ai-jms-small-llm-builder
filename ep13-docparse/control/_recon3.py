# -*- coding: utf-8 -*-
import json, os, glob, random, datetime, io, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(ROOT, 'cells', 'ep13-full-001')
ENGINES = ['oxr', 'paddleocr_vl', 'xiaomi_vl', 'ovis_ocr2', 'monkey_rec', 'surya_2_5']
man = json.load(open(os.path.join(ROOT, 'samples', 'manifest.json'), encoding='utf-8'))
img2sha = {s['img']: s['sha256'] for s in man['samples']}
sha2img = {v: k for k, v in img2sha.items()}
tasks = [(s['img'], e) for s in man['samples'] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != 'oxr']

st = json.load(open(os.path.join(ROOT, 'control', 'batch_state.json'), encoding='utf-8'))
consumed = int(st['seq'].split('/')[0]) - 1
print('NOW', datetime.datetime.now().strftime('%H:%M:%S'), 'seq', st['seq'],
      'consumed', consumed, 'n_run', st['n_run'], 'n_skip', st['n_skip'], 'n_fail', st['n_fail'])

files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
keys = []
for f in files:
    d = json.load(open(f, encoding='utf-8'))
    keys.append(((d.get('input') or {}).get('sha256'), d.get('engine'), os.path.basename(f)))
dup = [k for k, c in Counter((a, b) for a, b, _ in keys).items() if c > 1]
print('files=%d distinct_cells=%d duplicates=%d' % (len(files), len(set((a, b) for a, b, _ in keys)), len(dup)))
for k in dup:
    print('   DUP', k, [n for a, b, n in keys if (a, b) == k])

task_keys = [(img2sha[img], eng) for img, eng in tasks]
have = {(a, b) for a, b, _ in keys}
consumed_keys = set(task_keys[:consumed])
beyond = [k for k in have if k not in consumed_keys]
print('cells belonging to NOT-YET-CONSUMED tasks: %d' % len(beyond))
for k in beyond:
    print('   BEYOND', sha2img.get(k[0]), k[1])

incon = [k for k in consumed_keys if k in have]
missing = [k for k in task_keys[:consumed] if k not in have]
print('consumed_with_cell=%d missing=%d' % (len(incon), len(missing)))
print('n_run+n_skip=%d  (should equal consumed_with_cell if fails write no cell)' % (st['n_run'] + st['n_skip']))
print('missing_by_engine', dict(Counter(e for _, e in missing)))
