# -*- coding: utf-8 -*-
import json, os, glob, random, io, sys, datetime, statistics, time
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(ROOT, 'cells', 'ep13-full-001')
ENGINES = ['oxr', 'paddleocr_vl', 'xiaomi_vl', 'ovis_ocr2', 'monkey_rec', 'surya_2_5']
man = json.load(open(os.path.join(ROOT, 'samples', 'manifest.json'), encoding='utf-8'))
bad = [s['sample_id'] for s in man['samples'] if s['sample_id'] + '.png' != s['img']]
print('sample_id+".png" != img:', bad or 'none (all 26 match)')
img2sha = {s['img']: s['sha256'] for s in man['samples']}
sha2img = {v: k for k, v in img2sha.items()}
tasks = [(s['img'], e) for s in man['samples'] for e in ENGINES]
random.Random(1301).shuffle(tasks)
tasks = [t for t in tasks if t[1] != 'oxr']
print('tasks_after_filter=%d (batch_state total should match)' % len(tasks))

st = json.load(open(os.path.join(ROOT, 'control', 'batch_state.json'), encoding='utf-8'))
seq_done = int(st['seq'].split('/')[0]); total = int(st['seq'].split('/')[1])
consumed = seq_done - 1
files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
rows = [(f, json.load(open(f, encoding='utf-8'))) for f in files]
have = {((d.get('input') or {}).get('sha256'), d.get('engine')) for _, d in rows}
missing = [(i, im, e) for i, (im, e) in enumerate(tasks[:consumed], 1)
           if (img2sha[im], e) not in have]

print('SNAPSHOT %s' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
print('seq=%s current=%s desired=%s' % (st['seq'], st['current'], st.get('desired')))
print('n_run=%d n_skip=%d n_fail=%d sum=%d consumed=%d' % (
    st['n_run'], st['n_skip'], st['n_fail'], st['n_run'] + st['n_skip'] + st['n_fail'], consumed))
print('files=%d run+skip=%d diff=%d | missing=%d n_fail=%d diff=%d' % (
    len(files), st['n_run'] + st['n_skip'], st['n_run'] + st['n_skip'] - len(files),
    len(missing), st['n_fail'], len(missing) - st['n_fail']))
print('missing_by_engine', dict(Counter(e for _, _, e in missing)))
eng = defaultdict(Counter)
for _, d in rows:
    eng[d.get('engine')][d.get('status')] += 1
print('STATUS_BY_ENGINE', {k: dict(v) for k, v in sorted(eng.items())})
print('STATUS_TOTAL', dict(Counter(d.get('status') for _, d in rows)))

cer = [(d['cer_median'], d.get('engine'), sha2img.get((d.get('input') or {}).get('sha256'), '?'),
        datetime.datetime.fromtimestamp(os.path.getmtime(f)))
       for f, d in rows if isinstance(d.get('cer_median'), (int, float))]
norm = [c for c in cer if c[0] < 0.5]
out = sorted([c for c in cer if c[0] >= 0.5], reverse=True)
print('CER normal n=%d median=%.4f | outliers n=%d' % (
    len(norm), statistics.median([c[0] for c in norm]), len(out)))
KNOWN = {('xiaomi_vl', 'shot_01.png'), ('xiaomi_vl', 'table_01.png')}
sess0 = datetime.datetime(2026, 11, 5, 6, 50, 30).timestamp()
recent_out = 0
for c, e, img, mt in out:
    tag = 'KNOWN' if (e, img) in KNOWN else 'other'
    if mt.timestamp() >= time.time() - 3600:
        tag += '+LAST1H'
        recent_out += 1
    print('   %-14s cer=%.4f %-13s x %-16s landed=%s' % (tag, c, e, img, mt.strftime('%H:%M')))
print('outliers_outside_known=%d  landed_last_1h=%d' % (
    sum(1 for c, e, img, _ in out if (e, img) not in KNOWN), recent_out))

wall = [d['wall_median'] for _, d in rows if isinstance(d.get('wall_median'), (int, float))]
print('WALL median=%.1fs n=%d min=%.1f max=%.1f' % (
    statistics.median(wall), len(wall), min(wall), max(wall)))

sess_min = (time.time() - sess0) / 60.0
sess_consumed = consumed - 5
mts = sorted(os.path.getmtime(f) for f in files)
k = min(8, len(mts) - 1)
recent = (mts[-1] - mts[-1 - k]) / 60.0 / k
rem = total - seq_done + 1
print('RATE session=%.2f min/cell (consumed=%d in %.1fh) recent%d=%.2f remaining=%d' % (
    sess_min / max(sess_consumed, 1), sess_consumed, sess_min / 60, k, recent, rem))
print('ETA session=%.1fh recent=%.1fh' % ((sess_min / sess_consumed) * rem / 60, recent * rem / 60))
print('last_progress age=%.1f min last_file age=%.1f min' % (
    (datetime.datetime.now() - datetime.datetime.fromisoformat(st['last_progress'])).total_seconds() / 60,
    (time.time() - mts[-1]) / 60))
hb = json.load(open(os.path.join(ROOT, 'control', 'heartbeat.json'), encoding='utf-8'))
print('HEARTBEAT age_s=%.0f' % (time.time() - datetime.datetime.fromisoformat(hb['hb_at']).timestamp()))
task = json.load(open(os.path.join(ROOT, 'control', 'task.json'), encoding='utf-8'))
print('TASK', json.dumps(task, ensure_ascii=False))
