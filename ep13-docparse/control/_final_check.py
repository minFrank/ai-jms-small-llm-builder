# -*- coding: utf-8 -*-
import json, os, glob, io, sys, datetime, random, statistics, time
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(ROOT, 'cells', 'ep13-full-001')

files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
mism = 0
for f in files:
    base = os.path.basename(f)
    fn_eng = base.split('__')[1]
    d = json.load(open(f, encoding='utf-8'))
    if d.get('engine') != fn_eng:
        mism += 1
        print('ENGINE_MISMATCH', base, 'content=', d.get('engine'))
    if not os.path.exists(os.path.join(CELLS, base.replace('.json', '.tmp'))):
        pass
print('files=%d filename_vs_content_engine_mismatch=%d' % (len(files), mism))

# tmp/partial leftovers
left = [p for p in os.listdir(CELLS) if not p.endswith('.json')]
print('non-json leftovers:', left)

st = json.load(open(os.path.join(ROOT, 'control', 'batch_state.json'), encoding='utf-8'))
print('STATE', json.dumps(st, ensure_ascii=False))
print('NOW', datetime.datetime.now().strftime('%H:%M:%S'))
print('run+skip=%d files=%d n_fail=%d missing_expected=%d' % (
    st['n_run'] + st['n_skip'], len(files), st['n_fail'],
    int(st['seq'].split('/')[0]) - 1 - len(files)))

walls = [json.load(open(f, encoding='utf-8')).get('wall_median') for f in files]
walls = [w for w in walls if isinstance(w, (int, float))]
print('WALL median=%.1fs n=%d' % (statistics.median(walls), len(walls)))

sess0 = datetime.datetime(2026, 11, 5, 6, 50, 30).timestamp()
mts = sorted(os.path.getmtime(f) for f in files)
sess_n = sum(1 for m in mts if m >= sess0)
sess_rate = (mts[-1] - sess0) / 60.0 / max(sess_n, 1)
k = min(8, len(mts) - 1)
recent = (mts[-1] - mts[-1 - k]) / 60.0 / k
seq_done = int(st['seq'].split('/')[0])
rem = 130 - seq_done + 1
print('RATE session=%.2f recent%d=%.2f min/cell | remaining=%d | ETA session=%.1fh recent=%.1fh' % (
    sess_rate, k, recent, rem, sess_rate * rem / 60, recent * rem / 60))
print('last_progress age=%.1f min | last_file age=%.1f min' % (
    (datetime.datetime.now() - datetime.datetime.fromisoformat(st['last_progress'])).total_seconds() / 60,
    (time.time() - mts[-1]) / 60))
