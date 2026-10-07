#!/usr/bin/env python
"""ep04 阶段2 修复: 把散落的 external data 收敛成 model.onnx + model.onnx_data。

背景(REVIEW-export E2/E3/E4):
  torch.onnx.export 的 all_tensors_to_one_file=True 被静默忽略 → 散成几百个
  以 tensor 命名的文件;onnx.checker 用 proto 校验时按 cwd 解析 location → 假 FAIL。

修法(REVIEW-export §2.2 建议): torch 导出 → onnx 层 onnx.save_model 收敛。
跑完做三重校验: checker(传路径,自动 base_dir) + external 引用齐全 + ORT 冒烟。
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"D:/ep04/onnx/sd15"
PARTS = ["text_encoder", "unet", "vae"]
TIMEBOX = 900


def consolidate(part, t_start):
    import onnx
    d = os.path.join(BASE, part)
    opath = os.path.join(d, "model.onnx")
    if not os.path.exists(opath):
        raise RuntimeError(f"{part}: 缺 model.onnx")

    # 读 proto(相对 location 按 opath 所在目录解析)
    proto = onnx.load(opath, load_external_data=True)

    before = sorted(os.listdir(d))
    # 收敛成单个 data 文件
    onnx.save_model(proto, opath,
                    save_as_external_data=True,
                    all_tensors_to_one_file=True,
                    location="model.onnx_data",
                    size_threshold=1024,
                    convert_attribute=False)
    after = sorted(os.listdir(d))

    # 清掉收敛前的散文件(保留 model.onnx / model.onnx_data)
    keep = {"model.onnx", "model.onnx_data"}
    removed = 0
    for f in before:
        if f in keep:
            continue
        p = os.path.join(d, f)
        if os.path.isfile(p) and f not in after:
            continue
        if os.path.isfile(p) and f not in keep:
            try:
                os.remove(p)
                removed += 1
            except OSError:
                pass
    # 再清一次: 收敛后目录里除 keep 外一律删
    for f in sorted(os.listdir(d)):
        if f in keep:
            continue
        p = os.path.join(d, f)
        if os.path.isfile(p):
            try:
                os.remove(p)
                removed += 1
            except OSError:
                pass
    return opath, removed, before, after


def verify(part, opath):
    """三重校验(E4 修法): checker(路径) + external 引用齐全 + ORT 冒烟。"""
    import onnx
    import hashlib
    res = {}

    # 1) checker 传路径 → onnx 用文件目录做 base_dir 解析 external data
    m = onnx.load(opath, load_external_data=False)
    res["opset"] = [f"{x.domain or 'ai.onnx'}:{x.version}" for x in m.opset_import]
    onnx.checker.check_model(opath, full_check=True)
    res["checker"] = "ok(full_check)"

    # 2) external 引用必须齐全,且必须真的走 external(>1GB 的不可能全内嵌)
    refs = set()
    for t in m.graph.initializer:
        for kv in t.external_data:
            if kv.key == "location":
                refs.add(os.path.join(os.path.dirname(opath), kv.value))
    missing = [p for p in refs if not os.path.isfile(p)]
    if missing:
        raise RuntimeError(f"external data 缺失: {missing[:3]}")
    res["external_refs"] = len(refs)
    res["external_all_present"] = True

    # 3) ORT 冒烟: 真能建 session 就说明图+权重自洽
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.log_severity_level = 3
    sess = ort.InferenceSession(opath, opts,
                                providers=["DmlExecutionProvider", "CPUExecutionProvider"])
    res["ort_providers"] = sess.get_providers()
    res["ort_inputs"] = {i["name"]: i["type"] for i in sess.get_inputs()}
    res["ort_outputs"] = [o["name"] for o in sess.get_outputs()]

    # 4) 整组 sha256(B3)
    files = [opath] if os.path.isfile(opath) else []
    for r in sorted(refs):
        if os.path.isfile(r):
            files.append(r)
    h = hashlib.sha256()
    total = 0
    per = {}
    for f in files:
        hh = hashlib.sha256()
        with open(f, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                hh.update(blk)
                h.update(blk)
        per[os.path.basename(f)] = {"sha256": hh.hexdigest(),
                                    "size": os.path.getsize(f)}
        total += os.path.getsize(f)
        h.update(os.path.basename(f).encode())
    res["group_sha256"] = h.hexdigest()
    res["files"] = per
    res["total_bytes"] = total
    return res


def main():
    import onnx
    t_start = time.time()
    mp = os.path.join(BASE, "manifest.json")
    with open(mp, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest.setdefault("repair", {})

    for part in PARTS:
        if time.time() - t_start > TIMEBOX:
            manifest["repair"]["stop_reason"] = f"timebox {TIMEBOX}s"
            break
        print(f"[{time.strftime('%H:%M:%S')}] {part}...", flush=True)
        t0 = time.time()
        try:
            opath, removed, before, after = consolidate(part, t_start)
            print(f"  收敛: {len(before)} 文件 -> {len(after)} (删 {removed})", flush=True)
            r = verify(part, opath)
            r["consolidate_s"] = round(time.time() - t0, 1)
            r["precision"] = manifest.get("parts", {}).get(part, {}).get("precision")
            manifest["repair"][part] = r
            print(f"  checker={r['checker']} refs={r['external_refs']} "
                  f"providers={r['ort_providers']} "
                  f"total={r['total_bytes']/1024**3:.2f}GB "
                  f"sha={r['group_sha256'][:16]}…", flush=True)
        except Exception as e:
            manifest["repair"][part] = {"checker": f"FAIL: {type(e).__name__}: {str(e)[:400]}"}
            print(f"  FAIL: {type(e).__name__}: {str(e)[:400]}", flush=True)

    manifest["repair"]["elapsed_s"] = round(time.time() - t_start, 1)
    manifest["repair"]["cmdline"] = " ".join(sys.argv)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    bad = [p for p in PARTS
           if not str(manifest["repair"].get(p, {}).get("checker", "")).startswith("ok")]
    print(f"\nmanifest -> {mp}", flush=True)
    if bad:
        print(f"RESULT FAIL {bad}", flush=True)
        sys.exit(1)
    print("RESULT PASS", flush=True)


if __name__ == "__main__":
    main()
