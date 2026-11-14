import json, os, glob, collections, datetime, statistics
base = r'D:/study/ai-jms/ep13-docparse'
files = sorted(glob.glob(os.path.join(base,'cells/ep13-full-001/*.json')))
man = json.load(open(os.path.join(base,'samples/manifest.json'), encoding='utf-8'))
u2img = {s['sample_uuid']: s['img'] for s in man['samples']}
rows=[]
for f in files:
    d=json.load(open(f, encoding='utf-8'))
    d['_mt']=os.stat(f).st_mtime
    d['_name']=os.path.basename(f)
    rows.append(d)
rows.sort(key=lambda r: r['_mt'])
now=datetime.datetime.now().timestamp()
# recent cell inter-arrival (last 12 cells)
gaps=[]
prev=None
for r in rows[-12:]:
    if prev is not None:
        gaps.append((r['_mt']-prev)/60)
    prev=r['_mt']
print('GAPS_MIN_last11', [round(g,1) for g in gaps])
print('MEAN_GAP_MIN', round(statistics.mean(gaps),1), 'MED', round(statistics.median(gaps),1))
# per-cell wall median recent
print('WALL_LAST5', [(r['engine'], u2img.get(r['sample_id'],r['sample_id']), r['wall_median']) for r in rows[-5:]])
# outliers with mtime
out=[]
for r in rows:
    c=r.get('cer_median')
    if isinstance(c,(int,float)) and c>=0.5:
        out.append((c, r['engine'], u2img.get(r['sample_id'], r['sample_id']), r['_mt'], r['status']))
out.sort(reverse=True)
now=datetime.datetime.now().timestamp()
print('N_OUT', len(out))
for c,e,img,mt,st in out:
    print('  %.4f %-12s %-14s mtime=%s age_h=%.1f %s' % (c,e,img,datetime.datetime.fromtimestamp(mt).strftime('%m-%d %H:%M'), (now-mt)/3600, st))
# status distribution
print('STATUS', dict(collections.Counter(r['status'] for r in rows)))
# per engine cer median normal
for eng in sorted(set(r['engine'] for r in rows)):
    sub=[r['cer_median'] for r in rows if r['engine']==eng and r['cer_median']<0.5]
    allc=[r['cer_median'] for r in rows if r['engine']==eng]
    print('ENG', eng, 'n', len(allc), 'med_normal', round(statistics.median(sub),4) if sub else None, 'max', round(max(allc),4))
# reps sanity
bad=[r['_name'] for r in rows if r.get('n_valid',0)<6]
print('CELLS_NVALID_LT6', len(bad), bad[:10])
# newest overall
print('NEWEST', datetime.datetime.fromtimestamp(rows[-1]['_mt']), rows[-1]['_name'])
print('AGE_NEWEST_MIN', round((now-rows[-1]['_mt'])/60,1))
