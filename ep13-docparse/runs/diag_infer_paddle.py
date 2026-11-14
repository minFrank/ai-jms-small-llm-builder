import subprocess, os, json, threading, queue, sys
EP = r"D:/study/ai-jms/ep13-docparse"
py = EP + "/venvs/paddle/Scripts/python.exe"
p = subprocess.Popen([py, EP + "/scripts/worker.py"], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True, encoding="utf-8", bufsize=1, cwd=EP)
q, eq = queue.Queue(), queue.Queue()
threading.Thread(target=lambda: [q.put(l) for l in p.stdout], daemon=True).start()
threading.Thread(target=lambda: eq.put(p.stderr.read()), daemon=True).start()
def call(obj, t):
    p.stdin.write(json.dumps(obj) + "\n"); p.stdin.flush()
    return q.get(timeout=t)
print("boot:", q.get(timeout=30).strip(), flush=True)
print("hello ok:", json.loads(call(dict(cmd="hello", id=1, engine="paddleocr_vl"), 120))["ok"], flush=True)
print("load:", call(dict(cmd="load", id=2, engine="paddleocr_vl"), 400).strip(), flush=True)
img = r"D:/study/ai-jms/ai-jms-small-llm-builder/ep11-ocr/output/samples/hard_02.png"
r = call(dict(cmd="infer", id=3, path=img, max_new=2048), 400)
print("infer:", json.dumps(r, ensure_ascii=False, indent=1)[:1500], flush=True)
p.kill()
if not eq.empty():
    print("worker stderr:", eq.get_nowait()[-600:], flush=True)
