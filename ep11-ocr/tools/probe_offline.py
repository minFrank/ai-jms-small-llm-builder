# -*- coding: utf-8 -*-
"""断网 guard 自检：证明拦截真生效（与引擎尝试分开计数，评审 R39/R40）。"""
import json
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.environ["EP11_NETLOG"] = os.path.join(BASE, "logs", "net_selftest.jsonl")
import offline_guard  # noqa: E402

res = {"guard_loaded": bool(getattr(offline_guard, "ACTIVE", False)),
       "blocked": False, "err": ""}
try:
    urllib.request.urlopen("http://example.com", timeout=5)
except OSError as e:
    res["blocked"] = True
    res["err"] = "%s: %s" % (type(e).__name__, e)
except Exception as e:  # noqa
    res["err"] = "UNEXPECTED %s: %s" % (type(e).__name__, e)

# 旁路探针：不继承 guard 的子进程是否也被拦（明确记录未覆盖范围）
import subprocess
sub = subprocess.run([sys.executable, "-c",
                      "import urllib.request;urllib.request.urlopen('http://example.com',timeout=5)"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace",
                     timeout=60)
res["subprocess_rc"] = sub.returncode
res["subprocess_blocked"] = sub.returncode != 0
res["note"] = "subprocess does NOT inherit the guard (expected rc!=0 only if net is actually down)"

out = os.path.join(BASE, "logs", "net_selftest.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
sys.exit(0 if (res["guard_loaded"] and res["blocked"]) else 1)
