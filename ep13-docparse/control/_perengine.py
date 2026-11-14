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
files = sorted(glob.glob(os.path.join(CELLS, '*.json')))
rows = [(f, json.load(open(f, encoding='utf-8'))) for f in files]
have = {((d.get('input') or {}).get('sha256'), d.get('engine')) for _, d in rows}

# per-engine consumed vs done vs missing(=fail)
cons_e = Counter(e for _, e in tasks[:consumed])
done_e = Counter(d.get('engine') for _, d in rows)
miss = [(i, im, e) for i, (im, e) in enumerate(tasks[:consumed], 1)
        if (img2sha[im], e) not in have]
miss_e = Counter(e for _, _, e in miss)
print('PER-ENGINE  engine: consumed / cell_done / no_cell(=fail)')
for e in sorted(cons_e):
    print('  %-13s %3d / %3d / %3d   fail_rate=%.0f%%' % (
        e, cons_e[e], done_e.get(e, 0), miss_e.get(e, 0),
        100.0 * miss_e.get(e, 0) / cons_e[e]))
print('TOTAL %d / %d / %d' % (sum(cons_e.values()), sum(done_e.values()), sum(miss_e.values())))

# any cell with err / schema_err
errcells = [(os.path.basename(f), d.get('err'), d.get('status')) for f, d in rows
            if d.get('err') or d.get('status') != 'complete']
print('cells_with_err_or_noncomplete:', errcells or 'none')

# re-run evidence: same (sha,engine) appearing once only, but n_run mismatch
print('run+skip=%d files=%d diff=%d | missing=%d n_fail=%d diff=%d' % (
    st['n_run'] + st['n_skip'], len(files), st['n_run'] + st['n_skip'] - len(files),
    len(miss), st['n_fail'], len(miss) - st['n_fail']))
print('MISSING list:')
for i, im, e in miss:
    print('   seq%-4d %-16s %s' % (i, im, e))

sess0 = datetime.datetime(2026, 11, 5, 6, 50, 30).timestamp()
sess_min = (time.time() - sess0) / 60.0
sess_consumed = consumed - 5
mts = sorted(os.path.getmtime(f) for f in files)
k = min(8, len(mts) - 1)
recent = (mts[-1] - mts[-1 - k]) / 60.0 / k
rem = total - seq_done + 1
print('RATE session=%.2f min/cell (consumed=%d in %.1fh) recent%d=%.2f remaining=%d' % (
    sess_min / sess_consumed, sess_consumed, sess_min / 60, k, recent, rem))
print('ETA session=%.1fh recent=%.1fh' % ((sess_min / sess_consumed) * rem / 60, recent * rem / 60))
print('NOW %s | last_progress age=%.1f min | last_file age=%.1f min' % (
    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    (datetime.datetime.now() - datetime.datetime.fromisoformat(st['last_progress'])).total_seconds() / 60,
    (time.time() - mts[-1]) / 60))
