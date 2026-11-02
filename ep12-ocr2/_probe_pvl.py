
import json, subprocess, sys
out = {}
try:
    import paddlex; out["paddlex"] = getattr(paddlex,"__version__","?")
except Exception as e: out["paddlex_err"]=str(e)[:150]
try:
    import paddle; out["paddle"]=paddle.__version__; out["gpu"]=paddle.is_compiled_with_gpu()
except Exception as e: out["paddle_err"]=str(e)[:150]
# paddlex 是否支持 PaddleOCR-VL
try:
    from paddlex import create_model
    m = create_model("PaddleOCR_VL_0_9B")
    out["create_PVL"]="ok"
except Exception as e:
    out["create_PVL_err"]=str(e)[:300]
# transformers 是否可用
try:
    import transformers; out["transformers"]=transformers.__version__
except Exception as e: out["transformers_err"]=str(e)[:100]
print(json.dumps(out, ensure_ascii=False, indent=2))
