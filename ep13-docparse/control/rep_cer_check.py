import json, os, glob, statistics, collections
base = r'D:/study/ai-jms/ep13-docparse'
files = glob.glob(os.path.join(base,'cells/ep13-full-001/*.json'))
neg=[]; nulls=[]
vals=[]
for f in files:
    d=json.load(open(f, encoding='utf-8'))
    c=d.get('cer_median')
    if c is None: nulls.append(os.path.basename(f))
    elif c<0: neg.append((c, d['engine'], d['sample_id']))
    else: vals.append(c)
print('NULL_CER', len(nulls), nulls)
print('NEG_CER', len(neg), neg)
vals.sort()
print('N_POS', len(vals), 'MED', round(statistics.median(vals),6))
lt=[v for v in vals if v<0.5]
print('N_LT0.5', len(lt), 'MED', round(statistics.median(lt),6))
print('N_GE0.5', sum(1 for v in vals if v>=0.5))
# oxr cells today re-run check
import datetime
oxr=[(os.path.getmtime(f), os.path.basename(f)) for f in files if json.load(open(f,encoding='utf-8'))['engine']=='oxr']
oxr.sort()
print('OXR_TODAY', sum(1 for t,_ in oxr if datetime.datetime.fromtimestamp(t).date()==datetime.date(2026,11,7)), '/', len(oxr))
