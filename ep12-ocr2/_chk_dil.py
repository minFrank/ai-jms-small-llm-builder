
import sys, json
sys.path.insert(0, r"D:/study/ai-jms/ep12-ocr2-venvs")
from engine_base_ep12 import ENGINES
out = {}
for name in ("rapidocrlite-medium", "rapidocrlite-small"):
    e = ENGINES[name]()
    e.load()
    impl = getattr(e, "_impl", None)
    inner = None
    for attr in ("_engine", "ocr", "engine", "_ocr"):
        if hasattr(impl, attr):
            inner = getattr(impl, attr); break
    rec = {"impl_class": type(impl).__name__, "inner_class": type(inner).__name__ if inner else None}
    hits = {}
    def walk(o, path, depth=0):
        if depth > 3: return
        for k in dir(o):
            if k.startswith("__"): continue
            try: v = getattr(o, k)
            except Exception: continue
            if "dilat" in k.lower():
                hits[path+"."+k] = (v if not callable(v) else "<callable>")
            elif hasattr(v, "__dict__") and not isinstance(v, (str, bytes, int, float, list, dict)):
                walk(v, path+"."+k, depth+1)
    walk(impl, "impl")
    rec["dilation_attrs"] = hits
    out[name] = rec
    e.unload()
print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:2200])
