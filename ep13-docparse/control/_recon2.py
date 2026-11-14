# -*- coding: utf-8 -*-
import json, os, glob, random, datetime, io, sys, statistics
from collections import Counter, defaultdict
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
seq_done = int(st['seq'].split('/')[0])
consumed = seq_done - 1
print('NOW', datetime.datetime.now().strftime('%H:%M:%S'), 'seq', st['seq'], 'consumed', consumed)
print('n_run=%d n_skip=%d n_fail=%d' % (st['n_run'], st['n_skip'], st['n_fail']))

files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
rows = [json.load(open(f, encoding='utf-8')) for f in files]
have = {}
badsha = 0
for f, d in zip(files, rows):
    sha = (d.get('input') or {}).get('sha256')
    if sha not in sha2img:
        badsha += 1
        print('  SHA_NOT_IN_MANIFEST', os.path.basename(f), sha)
    have[(sha, d.get('engine'))] = os.path.basename(f)
print('files=%d  sha_not_in_manifest=%d' % (len(files), badsha))

missing = [(i, img, eng) for i, (img, eng) in enumerate(tasks[:consumed], 1)
           if (img2sha[img], eng) not in have]
print('MISSING(consumed but no cell)=%d' % len(missing))
byeng = Counter(e for _, _, e in missing)
print('MISSING_BY_ENGINE', dict(byeng))
print('CELLS_BY_ENGINE', dict(Counter(d.get('engine') for d in rows)))
for i, img, eng in missing:
    print('   miss seq%-4d %s x %s' % (i, img, eng))

# which consumed tasks are NOT missing (have cell) vs n_skip/n_run
print('run+skip=%d  files=%d  diff=%d' % (st['n_run'] + st['n_skip'], len(files),
                                          st['n_run'] + st['n_skip'] - len(files)))
print('missing=%d  n_fail=%d  diff=%d' % (len(missing), st['n_fail'], len(missing) - st['n_fail']))

# outlier mtimes (recent first)
out = [(d['cer_median'], d.get('engine'), sha2img.get((d.get('input') or {}).get('sha256'), '?'),
        datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(
            CELLS, have[((d.get('input') or {}).get('sha256'), d.get('engine'))]))))
       for d in rows if isinstance(d.get('cer_median'), (int, float)) and d['cer_median'] >= 0.5]
out.sort(key=lambda x: -x[0])
print('OUTLIERS n=%d' % len(out))
for c, e, img, mt in out:
    print('   %.4f %-13s %-16s landed=%s' % (c, e, img, mt.strftime('%m-%d %H:%M')))
