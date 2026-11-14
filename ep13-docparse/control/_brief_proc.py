# -*- coding: utf-8 -*-
import subprocess, sys, io, datetime, os, glob, json, statistics
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ps = r"(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'batch_runner' } | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CreationDate + ' | ' + $_.CommandLine.Substring(0,[Math]::Min(200,$_.CommandLine.Length)) }) -join [char]10"
out = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('BATCH_PROCS rc=%s' % out.returncode)
print(out.stdout.strip() or '(none)')
if out.stderr.strip():
    print('ERR:', out.stderr.strip()[:300])

# heartbeat age
hb = json.load(open(r'D:/study/ai-jms/ep13-docparse/control/heartbeat.json', encoding='utf-8'))
now = datetime.datetime.now()
hb_at = datetime.datetime.strptime(hb['hb_at'], '%Y-%m-%dT%H:%M:%S')
print('HEARTBEAT:', hb, 'age_min=%.1f' % ((now - hb_at).total_seconds() / 60))

# rate: last N cell mtimes
files = glob.glob(r'D:/study/ai-jms/ep13-docparse/cells/ep13-full-001/*.json')
mts = sorted(datetime.datetime.fromtimestamp(os.path.getmtime(f)) for f in files)
print('n_cells=%d first=%s last=%s' % (len(files), mts[0], mts[-1]))
# per-hour counts in last 12h
from collections import Counter
c = Counter(m.strftime('%m-%d %H') for m in mts)
for k in sorted(c)[-14:]:
    print('  hour', k, c[k])
# inter-cell gaps in last 30 cells
gaps = [(mts[i+1]-mts[i]).total_seconds()/60 for i in range(len(mts)-30, len(mts)-1)]
gaps = [g for g in gaps if 0 <= g < 180]
if gaps:
    print('LAST30_GAP_MEDIAN_MIN: %.1f' % statistics.median(gaps))
