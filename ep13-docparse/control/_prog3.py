# -*- coding: utf-8 -*-
import json, os, glob, datetime, statistics
BASE = r'D:/study/ai-jms/ep13-docparse'
CELLS = os.path.join(BASE, 'cells', 'ep13-full-001')
man = json.load(open(os.path.join(BASE, 'samples', 'manifest.json'), encoding='utf-8'))
u2s = {s['sample_uuid']: s['sample_id'] for s in man['samples']}
start = datetime.datetime.strptime('2026-11-06T14:07:23', '%Y-%m-%dT%H:%M:%S').timestamp()

# one failed oxr
p = sorted(glob.glob(os.path.join(CELLS, '*__oxr__*.json')))[0]
d = json.load(open(p, encoding='utf-8'))
print('OXR sample fail json:', os.path.basename(p))
for k in ('status', 'engine', 'err', 'err_kind', 'n_attempt', 'n_valid', 'target_valid', 'max_attempts', 'reps', 'wall_median'):
    print('   ', k, '=', d.get(k))

# in-batch completions rate
comp = []
for f in glob.glob(os.path.join(CELLS, '*.json')):
    t = os.path.getmtime(f)
    if t >= start:
        dd = json.load(open(f, encoding='utf-8'))
        if dd.get('status') == 'complete':
            comp.append((t, dd.get('engine'), u2s.get(os.path.basename(f).split('__')[0])))
comp.sort()
print('in-batch complete:', [(datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S'), e, s) for t, e, s in comp])
if len(comp) >= 2:
    print('complete-only rate: %.1f min/cell over %.1f min' % ((comp[-1][0]-comp[0][0])/60/(len(comp)-1), (comp[-1][0]-comp[0][0])/60))

# monkey_rec recent inter-completion
mrec = sorted(os.path.getmtime(f) for f in glob.glob(os.path.join(CELLS, '*__monkey_rec__*.json')))
print('monkey_rec last 6 mtimes:', [datetime.datetime.fromtimestamp(t).strftime('%d %H:%M:%S') for t in mrec[-6:]])
last6 = mrec[-6:]
deltas = [(last6[i+1]-last6[i])/60 for i in range(len(last6)-1)]
print('monkey_rec recent deltas min:', ['%.1f' % x for x in deltas], 'median=%.1f' % statistics.median(deltas))

# gap check
allm = sorted(os.path.getmtime(f) for f in glob.glob(os.path.join(CELLS, '*.json')))
gaps = [(allm[i+1]-allm[i])/3600 for i in range(len(allm)-1)]
gi = max(range(len(gaps)), key=lambda i: gaps[i])
print('biggest gap in cells: %.1f h between %s and %s' % (gaps[gi], datetime.datetime.fromtimestamp(allm[gi]), datetime.datetime.fromtimestamp(allm[gi+1])))
print('files written between 14:07 and 22:00:', sum(1 for t in allm if start <= t < datetime.datetime.strptime('2026-11-06T22:00','%Y-%m-%dT%H:%M').timestamp()))

# remaining queue estimate
tot = 156
processed = 119
files = len(allm)
have_file_unprocessed = files - processed
no_file = tot - files
print('processed=%d, unprocessed_with_file=%d, unprocessed_no_file=%d' % (processed, have_file_unprocessed, no_file))
