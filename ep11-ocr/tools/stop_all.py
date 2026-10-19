import os
import time
import psutil
ME = os.getpid()
KEYS = ('driver.py', 'bench_cell.py', 'batch_throughput.py', 'probe_offline.py')
for round_ in range(8):
    tgt = []
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            if p.pid == ME:
                continue
            cl = ' '.join(p.info['cmdline'] or [])
            if any(k in cl for k in KEYS):
                tgt.append((p.pid, cl[:60]))
        except Exception:
            pass
    if not tgt:
        print('round %d: clean' % round_)
        break
    for pid, _ in tgt:
        try:
            psutil.Process(pid).kill()
        except Exception:
            pass
    print('round %d killed %d -> %s' % (round_, len(tgt), [t[0] for t in tgt]))
    time.sleep(2)
time.sleep(8)
left = []
for p in psutil.process_iter(['pid', 'cmdline']):
    try:
        cl = ' '.join(p.info['cmdline'] or [])
        if any(k in cl for k in KEYS) and p.pid != ME:
            left.append((p.pid, cl[:70]))
    except Exception:
        pass
print('LEFT', left)
print('CLEAN' if not left else 'STILL_DIRTY')
