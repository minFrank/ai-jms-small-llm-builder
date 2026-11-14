# -*- coding: utf-8 -*-
import json, os, glob, random, io, sys, datetime
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r'D:/study/ai-jms/ep13-docparse'
ENGINES = ['oxr', 'paddleocr_vl', 'xiaomi_vl', 'ovis_ocr2', 'monkey_rec', 'surya_2_5']
man = json.load(open(os.path.join(ROOT, 'samples', 'manifest.json'), encoding='utf-8'))
img2sha = {s['img']: s['sha256'] for s in man['samples']}
sha2img = {v: k for k, v in img2sha.items()}
tasks = [(s['img'], e) for s in man['samples'] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != 'oxr']
st = json.load(open(os.path.join(ROOT, 'control', 'batch_state.json'), encoding='utf-8'))
consumed = int(st['seq'].split('/')[0]) - 1

# collect cells from ALL run dirs
allcells = {}
for p in glob.glob(os.path.join(ROOT, 'cells', '*', '*.json')):
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception:
        continue
    key = ((d.get('input') or {}).get('sha256'), d.get('engine'))
    allcells.setdefault(key, []).append(p)

main = os.path.join(ROOT, 'cells', 'ep13-full-001')
missing = []
for i, (img, eng) in enumerate(tasks[:consumed], 1):
    k = (img2sha[img], eng)
    if not any(os.path.dirname(p) == main for p in allcells.get(k, [])):
        missing.append((i, img, eng, allcells.get(k, [])))
print('MISSING in main=%d' % len(missing))
for i, img, eng, elsewhere in missing:
    print('  seq%-4d %-16s %-13s elsewhere=%s' % (
        i, img, eng, [os.path.relpath(p, ROOT) for p in elsewhere] or '-'))
