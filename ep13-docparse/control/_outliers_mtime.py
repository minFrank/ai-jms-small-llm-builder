# -*- coding: utf-8 -*-
import json, glob, os, io, sys, datetime, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = r'D:/study/ai-jms/ep13-docparse'
man = json.load(open(os.path.join(ROOT, 'samples/manifest.json'), encoding='utf-8'))
sha2img = {s['sha256']: s['img'] for s in man['samples']}
KNOWN = {('xiaomi_vl', 'shot_01.png'), ('xiaomi_vl', 'table_01.png')}
out = []
for p in glob.glob(os.path.join(ROOT, 'cells/ep13-full-001/*.json')):
    d = json.load(open(p, encoding='utf-8'))
    cer = d.get('cer_median')
    if isinstance(cer, (int, float)) and cer >= 0.5:
        img = sha2img.get((d.get('input') or {}).get('sha256'), '?')
        out.append((os.path.getmtime(p), cer, d['engine'], img, os.path.basename(p)))
out.sort()
print('OUTLIERS with completion time:')
for m, cer, e, img, f in out:
    tag = 'KNOWN' if (e, img) in KNOWN else 'other'
    print('  %s %.4f %s x %s  completed %s' % (tag, cer, e, img,
          datetime.datetime.fromtimestamp(m).strftime('%m-%d %H:%M:%S')))
print('count other =', sum(1 for m, c, e, i, f in out if (e, i) not in KNOWN))
# any outlier completed in last 6h?
cutoff = time.time() - 6 * 3600
print('completed in last 6h:', [(e, i, round(c, 4)) for m, c, e, i, f in out if m >= cutoff])
