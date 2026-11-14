# -*- coding: utf-8 -*-
import json, os, glob, random, io, sys, datetime, time, statistics
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
seq_done = int(st['seq'].split('/')[0]); total = int(st['seq'].split('/')[1])
consumed = seq_done - 1

entries = os.listdir(CELLS)
nonjson = [e for e in entries if not e.endswith('.json')]
print('DIR_ENTRIES=%d non_json=%s' % (len(entries), nonjson or 'none'))

files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
rows = [(f, json.load(open(f, encoding='utf-8'))) for f in files]
keys = [((d.get('input') or {}).get('sha256'), d.get('engine')) for _, d in rows]
badsha = sum(1 for k in keys if k[0] not in sha2img)
have = set(keys)
task_keys = [(img2sha[i], e) for i, e in tasks]
missing = [(i, im, e) for i, (im, e) in enumerate(tasks[:consumed], 1)
           if (img2sha[im], e) not in have]
cons_e = Counter(e for _, e in tasks[:consumed])
done_e = Counter(d.get('engine') for _, d in rows)
miss_e = Counter(e for _, _, e in missing)

print('== FINAL SNAPSHOT %s ==' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
print('seq=%s current=%s desired=%s' % (st['seq'], st['current'], st.get('desired')))
print('n_run=%d n_skip=%d n_fail=%d sum=%d consumed=%d' % (
    st['n_run'], st['n_skip'], st['n_fail'], st['n_run'] + st['n_skip'] + st['n_fail'], consumed))
print('files=%d distinct=%d sha_bad=%d | run+skip=%d diff=%d | missing=%d n_fail=%d diff=%d' % (
    len(files), len(have), badsha, st['n_run'] + st['n_skip'],
    st['n_run'] + st['n_skip'] - len(files), len(missing), st['n_fail'],
    len(missing) - st['n_fail']))
print('PER-ENGINE consumed/done/nocell:')
for e in sorted(cons_e):
    print('  %-13s %3d / %3d / %3d' % (e, cons_e[e], done_e.get(e, 0), miss_e.get(e, 0)))
print('STATUS_TOTAL', dict(Counter(d.get('status') for _, d in rows)))
print('NON_COMPLETE', [os.path.basename(f) for f, d in rows if d.get('status') != 'complete'] or 'none')

cer = [(d['cer_median'], d.get('engine'), sha2img.get((d.get('input') or {}).get('sha256'), '?'),
        datetime.datetime.fromtimestamp(os.path.getmtime(f)))
       for f, d in rows if isinstance(d.get('cer_median'), (int, float))]
norm = [c for c in cer if c[0] < 0.5]
out = sorted([c for c in cer if c[0] >= 0.5], reverse=True)
print('CER normal n=%d median=%.4f | outliers n=%d' % (
    len(norm), statistics.median([c[0] for c in norm]), len(out)))
KNOWN = {('xiaomi_vl', 'shot_01.png'), ('xiaomi_vl', 'table_01.png')}
for c, e, img, mt in out:
    tag = 'KNOWN' if (e, img) in KNOWN else 'other'
    if time.time() - mt.timestamp() < 3600:
        tag += '+LAST1H'
    print('   %-16s cer=%.4f %-13s x %-16s landed=%s' % (tag, c, e, img, mt.strftime('%H:%M')))
print('outliers_outside_known=%d landed_last_1h=%d' % (
    sum(1 for c, e, img, _ in out if (e, img) not in KNOWN),
    sum(1 for c, e, img, mt in out if time.time() - mt.timestamp() < 3600)))

wall = [d['wall_median'] for _, d in rows if isinstance(d.get('wall_median'), (int, float))]
print('WALL median=%.1fs n=%d min=%.1f max=%.1f' % (
    statistics.median(wall), len(wall), min(wall), max(wall)))

sess0 = datetime.datetime(2026, 11, 5, 6, 50, 30).timestamp()
now = time.time()
sess_min = (now - sess0) / 60.0
sess_consumed = consumed - 5
mts = sorted(os.path.getmtime(f) for f in files)
k = min(8, len(mts) - 1)
recent = (mts[-1] - mts[-1 - k]) / 60.0 / k
rem = total - seq_done + 1
print('RATE session=%.2f min/cell (consumed=%d in %.1fh) recent%d=%.2f remaining=%d' % (
    sess_min / sess_consumed, sess_consumed, sess_min / 60, k, recent, rem))
print('ETA session=%.1fh recent=%.1fh' % ((sess_min / sess_consumed) * rem / 60, recent * rem / 60))
print('last_progress age=%.1f min | last_file age=%.1f min | since_session_files=%d vs n_run=%d' % (
    (datetime.datetime.now() - datetime.datetime.fromisoformat(st['last_progress'])).total_seconds() / 60,
    (now - mts[-1]) / 60, sum(1 for m in mts if m >= sess0), st['n_run']))
hb = json.load(open(os.path.join(ROOT, 'control', 'heartbeat.json'), encoding='utf-8'))
task = json.load(open(os.path.join(ROOT, 'control', 'task.json'), encoding='utf-8'))
print('HEARTBEAT age_s=%.0f owner_pid=%s | TASK state=%s finished=%s' % (
    now - datetime.datetime.fromisoformat(hb['hb_at']).timestamp(), hb.get('owner_pid'),
    task.get('state'), task.get('finished_at')))
