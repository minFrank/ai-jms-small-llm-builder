# -*- coding: utf-8 -*-
import json, os, glob, io, sys
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(ROOT, 'cells', 'ep13-full-001')
man = json.load(open(os.path.join(ROOT, 'samples', 'manifest.json'), encoding='utf-8'))
sha2img = {s['sha256']: s['img'] for s in man['samples']}
img2sha = {s['img']: s['sha256'] for s in man['samples']}
mism = 0
for p in sorted(glob.glob(os.path.join(CELLS, '*.json'))):
    base = os.path.basename(p)
    fn_img = base.split('__')[0] + '.png'
    d = json.load(open(p, encoding='utf-8'))
    sha = (d.get('input') or {}).get('sha256')
    real = sha2img.get(sha, '?')
    if real != fn_img:
        mism += 1
        print('FILENAME_SHA_MISMATCH', base, '-> sha says', real)
print('files checked, filename-vs-sha mismatches =', mism)
# engine field vs filename engine
m2 = 0
for p in sorted(glob.glob(os.path.join(CELLS, '*.json'))):
    base = os.path.basename(p)
    d = json.load(open(p, encoding='utf-8'))
    if d.get('engine') != base.split('__')[1]:
        m2 += 1
        print('ENGINE_MISMATCH', base, d.get('engine'))
print('engine mismatches =', m2)
