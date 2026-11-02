
import json, glob, statistics, os
C = r"D:/study/ai-jms/ep12-ocr2-venvs/cells"
EXCL = {"book_02", "skew_02"}
out = {}
for eng in ["rapidocrlite-small","rapidocrlite-medium"]:
    cells = [json.loads(open(f,encoding="utf-8").read())
             for f in sorted(glob.glob(C+"/%s__*.json" % eng))]
    cells = [c for c in cells if not c.get("err") and c.get("median")]
    cer = [c.get("cer_main") for c in cells if c.get("cer_main") is not None]
    cer_all = sorted(cer)
    t = sorted(c["median"] for c in cells)
    rss = sorted(c["peak_rss_mb"] for c in cells if c.get("peak_rss_mb"))
    md = sorted(set(c["image"] for c in cells) & {"book_01","lowres_01","vert_01"})
    rows = {}
    for img in md:
        for c in cells:
            if c["image"]==img:
                rows[img] = {"cer": c.get("cer_main"), "t": round(c["median"],2)}
                break
    out[eng] = {"n": len(cells), "n_cer": len(cer_all),
        "cer_med": round(cer_all[len(cer_all)//2],4),
        "cer_mean": round(sum(cer_all)/len(cer_all),4),
        "t_med": round(t[len(t)//2],2),
        "rss_med": round(rss[len(rss)//2],1) if rss else None,
        "model_dir_bytes": None, "rows": rows}
    # 设置里的模型类型
    for c in cells:
        st = c.get("settings") or {}
        out[eng]["tier"] = st.get("tier")
        out[eng]["aligned"] = st.get("det_params_aligned_to_paddleocr")
        out[eng]["version"] = st.get("rapidocr_version")
        break
print(json.dumps(out, ensure_ascii=False, indent=2))
