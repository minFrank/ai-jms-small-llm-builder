import json, os, statistics, glob, collections
base = r'D:/study/ai-jms/ep13-docparse'
st = json.load(open(os.path.join(base,'control/batch_state.json'), encoding='utf-8'))
print('STATE', json.dumps(st, ensure_ascii=False))
files = sorted(glob.glob(os.path.join(base,'cells/ep13-full-001/*.json')))
print('NFILES', len(files))
rows=[]
for f in files:
    try:
        d=json.load(open(f, encoding='utf-8'))
    except Exception as e:
        print('BADJSON', f, e); continue
    rows.append((os.path.basename(f), d))
# top-level keys sample
keys=collections.Counter()
for n,d in rows:
    for k in d: keys[k]+=1
print('KEYS', dict(keys))
status=collections.Counter()
eng=collections.Counter()
eng_status=collections.Counter()
for n,d in rows:
    s=d.get('status')
    status[s]+=1
    e=d.get('engine') or n.split('__')[1] if '__' in n else d.get('engine')
    eng[d.get('engine')]+=1
    eng_status[(d.get('engine'),s)]+=1
print('STATUS', dict(status))
print('ENGINE', dict(eng))
print('ENG_STATUS', {f'{k[0]}|{k[1]}':v for k,v in eng_status.items()})
# CER
cers=[]
for n,d in rows:
    c=d.get('cer_median')
    if isinstance(c,(int,float)):
        cers.append((c, d.get('engine'), n, d.get('status')))
print('N_CER', len(cers))
vals=sorted(x[0] for x in cers)
if vals:
    print('CER_MEDIAN_ALL', statistics.median(vals))
norm=sorted(x[0] for x in cers if x[0]<0.5)
print('N_CER_LT0.5', len(norm), 'MED', statistics.median(norm) if norm else None)
out=sorted([x for x in cers if x[0]>=0.5], reverse=True)
print('OUTLIERS')
for c,e,n,s in out: print('  ', round(c,4), e, n, s)
walls=[d.get('wall_median') for n,d in rows if isinstance(d.get('wall_median'),(int,float))]
walls=sorted(walls)
print('N_WALL', len(walls), 'MED', statistics.median(walls) if walls else None)
# input sha
print('SHA_MISSING', sum(1 for n,d in rows if not d.get('input') or not d['input'].get('sha256') if isinstance(d.get('input'),dict)) )
# last_progress age
import datetime
lp=st.get('last_progress')
print('LAST_PROGRESS', lp)
# seq done?
print('SEQ', st.get('seq'), 'desired', st.get('desired'), 'finished', st.get('finished_at'))
