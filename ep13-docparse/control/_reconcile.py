# -*- coding: utf-8 -*-
import json, os, glob, datetime, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r'D:/study/ai-jms/ep13-docparse'
st = json.load(open(os.path.join(BASE, 'control', 'batch_state.json'), encoding='utf-8'))
files = glob.glob(os.path.join(BASE, 'cells', 'ep13-full-001', '*.json'))
sess0 = datetime.datetime(2026, 11, 5, 6, 50, 30).timestamp()
new = [f for f in files if os.path.getmtime(f) >= sess0]
old = [f for f in files if os.path.getmtime(f) < sess0]
print('NOW', datetime.datetime.now().strftime('%H:%M:%S'))
print('STATE', json.dumps(st, ensure_ascii=False))
print('FILES total=%d  since_session=%d  before_session=%d' % (len(files), len(new), len(old)))
print('n_run=%d n_skip=%d n_fail=%d  run+skip=%d  state_sum=%d' % (
    st['n_run'], st['n_skip'], st['n_fail'], st['n_run'] + st['n_skip'],
    st['n_run'] + st['n_skip'] + st['n_fail']))
hb = json.load(open(os.path.join(BASE, 'control', 'heartbeat.json'), encoding='utf-8'))
print('HEARTBEAT', json.dumps(hb, ensure_ascii=False),
      'age_s=%.0f' % (time.time() - datetime.datetime.fromisoformat(hb['hb_at']).timestamp()))
