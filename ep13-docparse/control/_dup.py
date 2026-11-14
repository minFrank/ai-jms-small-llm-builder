# -*- coding: utf-8 -*-
import json, os, glob, random, io, sys
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(ROOT, 'cells', 'ep13-full-001')
ENGINES = ['oxr', 'paddleocr_vl', 'xiaomi_vl', 'ovis_ocr2', 'monkey_rec', 'surya_2_5']
man = json.load(open(os.path.join(ROOT, 'samples', 'manifest.json'), encoding='utf-8'))
img2sha = {s['img']: s['sha256'] for s in man['samples']}
sha2imgs = defaultdict(list)
for s in man['samples']:
    sha2imgs[s['sha256']].append(s['img'])
dups = {k: v for k, v in sha2imgs.items() if len(v) > 1}
print('duplicate sha256 in manifest:', dups or 'none')

tasks = [(s['img'], e) for s in man['samples'] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != 'oxr']
st = json.load(open(os.path.join(ROOT, 'control', 'batch_state.json'), encoding='utf-8'))
consumed = int(st['seq'].split('/')[0]) - 1
files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
keys = []
for f in files:
    d = json.load(open(f, encoding='utf-8'))
    keys.append(((d.get('input') or {}).get('sha256'), d.get('engine'), os.path.basename(f)))
filekey = {(a, b) for a, b, _ in keys}
taskkey = [(img2sha[i], e) for i, e in tasks]
cons = taskkey[:consumed]
# how many consumed tasks are covered by file keys (counting multiplicity)
covered = sum(1 for k in cons if k in filekey)
print('consumed=%d files=%d distinct_file_keys=%d consumed_tasks_covered=%d' % (
    len(cons), len(files), len(filekey), covered))
# multiplicity: file keys used by >1 consumed task
keycount = Counter(cons)
multi = {k: c for k, c in keycount.items() if c > 1}
print('consumed keys appearing >1 time:', multi or 'none')
print('n_run+n_skip=%d  covered=%d  diff=%d' % (
    st['n_run'] + st['n_skip'], covered, st['n_run'] + st['n_skip'] - covered))
missing = [(i, tasks[i][0], tasks[i][1]) for i in range(consumed) if taskkey[i] not in filekey]
print('missing=%d n_fail=%d diff=%d' % (len(missing), st['n_fail'], len(missing) - st['n_fail']))
# pre-session files
sess0 = datetime = __import__('datetime').datetime(2026, 11, 5, 6, 50, 30).timestamp()
pre = [os.path.basename(f) for f in files if os.path.getmtime(f) < sess0]
print('pre_session_files=%d n_skip=%d' % (len(pre), st['n_skip']))
print('pre_session:', pre)
