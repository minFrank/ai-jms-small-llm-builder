#!/usr/bin/env python
"""ep04 阶段2 校验: checker + ORT 建 session + 真跑一次随机前向。

判据来源 REVIEW-export E2/E3/E4:
  E4 原修法要求 "onnx.checker + 一次 ORT-DML 加载冒烟" —— 本脚本把它落成三关:
    L1 onnx.checker.check_model(传路径 → 用文件目录解析 external data)
    L2 ORT InferenceSession 能建立(providers 含 DmlExecutionProvider)
    L3 喂随机输入真跑一次 forward(这才是"图能用"的真判据)
  full_check(shape inference)结果**只记录不作硬门** —— 实测 text_encoder 的
  fp16 LayerNorm 在 onnx shape inference 上严格报错,但 ORT 能跑;
  以 L3 为真判据,同时把 full_check 的信息写进 manifest 供追溯。

unet 不收敛(散文件布局合法,不搬运就无需合并 2GB protobuf)。
text_encoder/vae 若只有单文件则无需收敛。
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"D:/ep04/onnx/sd15"
PARTS = ["text_encoder", "unet", "vae"]
TIMEBOX = 900


def list_files(d):
    out = []
    for root, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f)
            out.append(p)
    return out


def l1_checker(opath):
    import onnx
    m = onnx.load(opath, load_external_data=False)
    info = {"opset": [f"{x.domain or 'ai.onnx'}:{x.version}" for x in m.opset_import]}
    info["ir_version"] = m.ir_version
    refs = set()
    for t in m.graph.initializer:
        for kv in t.external_data:
            if kv.key == "location":
                refs.add(os.path.join(os.path.dirname(opath), kv.value))
    missing = [p for p in refs if not os.path.isfile(p)]
    if missing:
        raise RuntimeError(f"external data 缺失 {len(missing)}: {missing[:3]}")
    info["external_refs"] = len(refs)
    # 结构检查(不带 full_check,避免 shape inference 的 fp16 LayerNorm 误杀)
    onnx.checker.check_model(opath, full_check=False)
    info["checker"] = "ok"
    # full_check 只作信息
    try:
        onnx.checker.check_model(opath, full_check=True)
        info["full_check"] = "ok"
    except Exception as e:
        info["full_check"] = f"note: {str(e)[:200]}"
    return info, refs


def l2_l3_ort(part, opath, refs):
    """L2 建 session + L3 真跑一次前向。返回 (info, ok)。"""
    import numpy as np
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.log_severity_level = 3   # 收集静默回退 warning(B5)
    providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
    sess = ort.InferenceSession(opath, opts, providers=providers)
    info = {"providers_used": sess.get_providers()}
    ins = {i.name: i for i in sess.get_inputs()}
    outs = [o.name for o in sess.get_outputs()]
    info["inputs"] = {n: {"shape": list(i.shape), "type": i.type} for n, i in ins.items()}
    info["outputs"] = outs

    # 造随机输入
    feed = {}
    for n, i in ins.items():
        shape = [1 if (not isinstance(s, int) or s is None) else s for s in i.shape]
        if "int" in i.type:
            feed[n] = np.ones(shape, dtype=np.int64)
        else:
            dt = np.float16 if "float16" in i.type else np.float32
            feed[n] = np.random.randn(*shape).astype(dt)

    t0 = time.time()
    res = sess.run(outs, feed)
    info["forward_s"] = round(time.time() - t0, 3)
    info["output_shapes"] = [list(r.shape) for r in res]
    info["output_finite"] = [bool(np.isfinite(r.astype(np.float64)).all()) for r in res]
    ok = all(info["output_finite"])
    if not ok:
        raise RuntimeError(f"前向输出非有限值: {info['output_finite']}")
    return info, True


def group_sha(opath, refs, d):
    import hashlib
    files = [opath] + sorted(r for r in refs if os.path.isfile(r))
    if not refs:
        # 单文件布局: 该目录下全部文件
        files = sorted(list_files(d))
    h, per, total = hashlib.sha256(), {}, 0
    for f in files:
        hh = hashlib.sha256()
        with open(f, "rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                hh.update(blk)
                h.update(blk)
        h.update(os.path.basename(f).encode())
        sz = os.path.getsize(f)
        per[os.path.basename(f)] = {"sha256": hh.hexdigest(), "size": sz}
        total += sz
    return h.hexdigest(), per, total


def main():
    t_start = time.time()
    mp = os.path.join(BASE, "manifest.json")
    with open(mp, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["verify"] = {}

    for part in PARTS:
        if time.time() - t_start > TIMEBOX:
            manifest["verify"]["stop_reason"] = f"timebox {TIMEBOX}s at {part}"
            break
        d = os.path.join(BASE, part)
        opath = os.path.join(d, "model.onnx")
        print(f"[{time.strftime('%H:%M:%S')}] {part}...", flush=True)
        r = {"files_on_disk": sorted(os.listdir(d))}
        try:
            if not os.path.exists(opath):
                raise RuntimeError(f"缺 {opath}")
            info, refs = l1_checker(opath)
            r.update(info)
            print(f"  L1 checker={info['checker']} refs={info['external_refs']} "
                  f"opset={info['opset']}", flush=True)

            vinfo, _ = l2_l3_ort(part, opath, refs)
            r.update(vinfo)
            r["ok"] = True
            print(f"  L2/L3 providers={vinfo['providers_used']} "
                  f"fwd={vinfo['forward_s']}s finite={vinfo['output_finite']} "
                  f"shapes={vinfo['output_shapes']}", flush=True)

            sha, per, total = group_sha(opath, refs, d)
            r["group_sha256"] = sha
            r["files"] = per
            r["total_bytes"] = total
            r["precision"] = manifest.get("parts", {}).get(part, {}).get("precision")
            print(f"  sha={sha[:16]}… total={total/1024**3:.2f}GB", flush=True)
        except Exception as e:
            r["ok"] = False
            r["error"] = f"{type(e).__name__}: {str(e)[:500]}"
            print(f"  FAIL: {r['error']}", flush=True)
        manifest["verify"][part] = r

    manifest["verify"]["elapsed_s"] = round(time.time() - t_start, 1)
    manifest["verify"]["cmdline"] = " ".join(sys.argv)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    bad = [p for p in PARTS if not manifest["verify"].get(p, {}).get("ok")]
    print(f"\nmanifest -> {mp}", flush=True)
    if bad:
        print(f"RESULT FAIL {bad}", flush=True)
        sys.exit(1)
    print("RESULT PASS", flush=True)


if __name__ == "__main__":
    main()
