# -*- coding: utf-8 -*-
"""Fresh consistent snapshot: state vs cells reconciliation."""
import json, glob, os, io, sys, random, datetime, time, statistics
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = r'D:/study/ai-jms/ep13-docparse'

def snap():
    st = json.load(open(os.path.join(ROOT, 'control/batch_state.json'), encoding='utf-8'))
    man = json.load(open(os.path.join(ROOT, 'samples/manifest.json'), encoding='utf-8'))
    img2sha = {s['img']: s['sha256'] for s in man['samples']}
    sha2img = {v: k for k, v in img2sha.items()}
    ENGINES = ["oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"]
    tasks = [(s['sample_id'] + '.png', e) for s in man['samples'] for e in ENGINES]
    random.Random(1301).shuffle(tasks)
    tasks = [t for t in tasks if t[1] != 'oxr']
    files = glob.glob(os.path.join(ROOT, 'cells/ep13-full-001/*.json'))
    rows = [(p, json.load(open(p, encoding='utf-8'))) for p in files]
    have = {((d.get('input') or {}).get('sha256'), d.get('engine')): p for p, d in rows}
    return st, tasks, img2sha, sha2img, files, rows, have

# take two snapshots 3s apart to catch a mid-write state
s1 = snap()
time.sleep(3)
s2 = snap()

st, tasks, img2sha, sha2img, files, rows, have = s2
consumed = int(st['seq'].split('/')[0]) - 1
missing = [(i, img, eng) for i, (img, eng) in enumerate(tasks[:consumed], 1)
           if (img2sha[img], eng) not in have]
sess0 = datetime.datetime(2026, 11, 5, 6, 50, 31).timestamp()
since = sum(1 for p in files if os.path.getmtime(p) >= sess0)
before = len(files) - since

print('T1 seq=%s run=%d skip=%d fail=%d files=%d' % (
    s1[0]['seq'], s1[0]['n_run'], s1[0]['n_skip'], s1[0]['n_fail'], len(s1[4])))
print('T2 NOW=%s seq=%s current=%s run=%d skip=%d fail=%d sum=%d last_progress=%s desired=%s' % (
    datetime.datetime.now().strftime('%H:%M:%S'), st['seq'], st['current'],
    st['n_run'], st['n_skip'], st['n_fail'],
    st['n_run'] + st['n_skip'] + st['n_fail'], st['last_progress'], st.get('desired')))
print('FILES total=%d since_batch=%d before=%d | run+skip=%d' % (
    len(files), since, before, st['n_run'] + st['n_skip']))
print('CONSUMED=%d MISSING_among_consumed=%d | n_fail=%d -> diff=%d' % (
    consumed, len(missing), st['n_fail'], len(missing) - st['n_fail']))
print('GAP_BY_ENGINE', dict(Counter(e for _, _, e in missing)))
print('GAP', missing)

es = defaultdict(Counter)
for p, d in rows:
    es[d['engine']][d['status']] += 1
print('STATUS_BY_ENGINE', {k: dict(v) for k, v in sorted(es.items())})
print('TOTAL_STATUS', dict(Counter(d['status'] for _, d in rows)))
non_complete = [(os.path.basename(p), d.get('status')) for p, d in rows if d.get('status') != 'complete']
print('NON_COMPLETE', non_complete)

cer = [(d['cer_median'], d['engine'], sha2img.get((d.get('input') or {}).get('sha256'), '?'), p)
       for p, d in rows if isinstance(d.get('cer_median'), (int, float))]
normal = [c[0] for c in cer if c[0] < 0.5]
out = sorted([c for c in cer if c[0] >= 0.5], reverse=True)
print('CER normal n=%d median=%.4f | outliers=%d' % (
    len(normal), statistics.median(normal), len(out)))
KNOWN = {('xiaomi_vl', 'shot_01.png'), ('xiaomi_vl', 'table_01.png')}
for v, e, img, p in out:
    mt = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%m-%d %H:%M')
    print('   %s cer=%.4f %s x %s  done=%s' % (
        'KNOWN' if (e, img) in KNOWN else 'other', v, e, img, mt))

wall = [d['wall_median'] for _, d in rows if isinstance(d.get('wall_median'), (int, float))]
print('WALL median=%.1fs n=%d min=%.1f max=%.1f' % (
    statistics.median(wall), len(wall), min(wall), max(wall)))

mts = sorted(os.path.getmtime(p) for p in files)
now = time.time()
sess_n = sum(1 for m in mts if m >= sess0)
sess_rate = (mts[-1] - sess0) / 60.0 / max(sess_n, 1)
k = min(8, len(mts) - 1)
recent = (mts[-1] - mts[-1 - k]) / 60.0 / k
allr = (mts[-1] - mts[0]) / 60.0 / (len(mts) - 1)
rem = len(tasks) - consumed
print('RATE session=%.2f recent%d=%.2f all=%.2f min/cell | remaining=%d' % (
    sess_rate, k, recent, allr, rem))
print('ETA session=%.1fh recent=%.1fh all=%.1fh' % (
    sess_rate * rem / 60, recent * rem / 60, allr * rem / 60))
print('LAST_FILE %s age=%.1fmin | last_progress age=%.1fmin' % (
    datetime.datetime.fromtimestamp(mts[-1]).strftime('%H:%M:%S'),
    (now - mts[-1]) / 60,
    (datetime.datetime.now() - datetime.datetime.fromisoformat(st['last_progress'])).total_seconds() / 60))
hb = json.load(open(os.path.join(ROOT, 'control/heartbeat.json'), encoding='utf-8'))
print('HEARTBEAT', hb, 'age_s=%.0f' % (now - datetime.datetime.fromisoformat(hb['hb_at']).timestamp()))
