"""D 组：分母/工期表 + 跨文件断言（dsh r4 D 组判据）
跑法: python scripts/test_denominators.py
"""
import sys, os, math, re, json
PASS, FAIL = 0, []
def check(name, cond, detail=""):
    global PASS
    if cond: PASS += 1
    else: FAIL.append(f"{name}: {detail}")

EP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = r"C:/Users/Frank/AppData/Local/hermes/.hermes/plans/2026-11-03-docparse-bench-console-spec.md"

# ---------- 算术 ----------
check("D-156", 26*6 == 156)
check("D-144", 24*6 == 144)
check("D-149", math.ceil(156*0.95) == 149)
check("D-137", math.ceil(144*0.95) == 137)
check("D-1872", 156*12 == 1872)
check("D-1728", 144*12 == 1728)
check("D-25", math.ceil(26*0.95) == 25)
check("D-23", math.ceil(24*0.95) == 23)
check("D-1092", 156*7 == 1092)                      # 6 valid+1 容错/格
mean = (60+161+241+993+308+983)/6
check("D-457.7", abs(mean-457.666) < 0.01, f"{mean}")
check("D-138.8h", abs(1092*mean/3600 - 138.8) < 0.1, f"{1092*mean/3600}")
check("D-238h", abs(1872*mean/3600 - 238.0) < 0.1, f"{1872*mean/3600}")

# ---------- sets.yaml ↔ V6d 跨文件 ----------
sets = open(os.path.join(EP, "control", "sets.yaml"), encoding="utf-8").read()
spec = open(SPEC, encoding="utf-8").read() if os.path.exists(SPEC) else ""
check("D-sets-156", "expected_cells: 156" in sets)
check("D-sets-149", "min_complete_cells: 149" in sets)
check("D-sets-1872", "max_reps: 1872" in sets)
check("D-sets-1092", "expected_reps: 1092" in sets)
# 规格跨文件（存在才断言；r4 要求）
if spec:
    check("D-spec-156", re.search(r"156", spec) is not None)
    check("D-spec-no2496", "2496" not in spec, "V6d 残留 2496")
    check("D-spec-nopage_sha", "page_sha" not in spec, "V6d 残留 page_sha")
    check("D-spec-SALL", "156 + S_PDF" in spec or "156+S_PDF" in spec, "S_ALL 未=156+S_PDF")
    check("D-spec-F01", re.search(r"F-01[^0-9]{0,40}1872", spec) is not None, "F-01 未=1872")
else:
    FAIL.append("D-spec: 规格文件缺失")

# ---------- engines.yaml wall 表冻结 ----------
eng = open(os.path.join(EP, "control", "engines.yaml"), encoding="utf-8").read()
for e in ("oxr", "paddleocr_vl", "xiaomi_vl", "ovis_ocr2", "monkey_rec", "surya_2_5"):
    check(f"D-wall-{e}", e in eng and "wall:" in eng)
check("D-layer-A", eng.count("layer: A") >= 1 or "defaults" in eng)

print(f"D 组: PASS={PASS}  FAIL={len(FAIL)}")
for f in FAIL: print("  ✗", f)
sys.exit(1 if FAIL else 0)
