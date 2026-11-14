# -*- coding: utf-8 -*-
import sys
try:
    import psutil
except Exception as e:
    print("NO_PSUTIL", e)
    sys.exit(0)
hits = []
for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
    try:
        cl = " ".join(p.info.get("cmdline") or [])
    except Exception:
        continue
    if "batch_runner" in cl:
        hits.append((p.info["pid"], p.info["name"], p.info["create_time"], cl[:200]))
print("BATCH_RUNNER_COUNT:", len(hits))
for h in hits:
    print("  PID=%s NAME=%s CT=%s CMD=%s" % h)
import datetime, os
try:
    st = psutil.Process(24240)
    print("PID24240_ALIVE:", True, st.name(), " ".join(st.cmdline()[:6]))
except Exception as e:
    print("PID24240_ALIVE:", False, e)
