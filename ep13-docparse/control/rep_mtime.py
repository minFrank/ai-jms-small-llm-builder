import json, os, glob, collections, datetime, statistics
base = r'D:/study/ai-jms/ep13-docparse'
files = sorted(glob.glob(os.path.join(base,'cells/ep13-full-001/*.json')))
sets = collections.Counter(); layers = collections.Counter()
mt = []
rows=[]
for f in files:
    d=json.load(open(f, encoding='utf-8'))
    sets[d.get('set')]+=1; layers[d.get('layer')]+=1
    st=os.stat(f)
    mt.append((st.st_mtime, os.path.basename(f), d.get('engine'), d.get('sample_id'), d.get('status')))
    rows.append(d)
print('SETS', dict(sets))
print('LAYERS', dict(layers))
mt.sort()
now=datetime.datetime.now().timestamp()
print('OLDEST', datetime.datetime.fromtimestamp(mt[0][0]), mt[0][1])
print('NEWEST', datetime.datetime.fromtimestamp(mt[-1][0]), mt[-1][1])
print('AGE_NEWEST_MIN', round((now-mt[-1][0])/60,1))
# last 10
for t,n,e,s,stt in mt[-10:]:
    print('  ', datetime.datetime.fromtimestamp(t).strftime('%m-%d %H:%M:%S'), n, stt)
# mtime distribution per hour
hours=collections.Counter(datetime.datetime.fromtimestamp(t).strftime('%m-%d %H') for t,_,_,_,_ in mt)
print('BY_HOUR', dict(sorted(hours.items())))
# per engine sample counts + newest
for eng in sorted(set(r.get('engine') for r in rows)):
    sub=[m for m in mt if m[2]==eng]
    print('ENG', eng, len(sub), 'newest', datetime.datetime.fromtimestamp(sub[-1][0]).strftime('%m-%d %H:%M:%S'))
