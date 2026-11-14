# -*- coding: utf-8 -*-
import json, os, glob, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(ROOT, 'cells', 'ep13-full-001')
man = json.load(open(os.path.join(ROOT, 'samples', 'manifest.json'), encoding='utf-8'))
uuid2img = {s['sample_uuid']: s['img'] for s in man['samples']}
sha2img = {s['sha256']: s['img'] for s in man['samples']}
bad = 0
for p in sorted(glob.glob(os.path.join(CELLS, '*.json'))):
    base = os.path.basename(p)
    u = base.split('__')[0]
    d = json.load(open(p, encoding='utf-8'))
    sha = (d.get('input') or {}).get('sha256')
    fn_img = uuid2img.get(u, 'UNKNOWN_UUID')
    sha_img = sha2img.get(sha, 'UNKNOWN_SHA')
    if fn_img != sha_img:
        bad += 1
        print('UUID_SHA_MISMATCH', base, 'filename->', fn_img, 'sha->', sha_img)
print('checked=%d uuid_vs_sha_mismatches=%d' % (len(glob.glob(os.path.join(CELLS, '*.json'))), bad))
