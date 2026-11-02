import sys, time, traceback, os
print("python:", sys.version.split()[0])
t0 = time.time()
try:
    import rapidocr
    print("import rapidocr OK, %.2fs" % (time.time() - t0))
    print("模块路径:", rapidocr.__file__)
    from rapidocr import RapidOCR
    print("RapidOCR 类 OK")
    import inspect
    sig = inspect.signature(RapidOCR.__init__)
    print("构造参数:", list(sig.parameters.keys())[:10])
    # 看默认模型变体（STEP 0 manifest 要的 det/rec 变体线索）
    try:
        from rapidocr.utils.logger import logger  # noqa
    except Exception:
        pass
    # 找内置模型目录
    pkg = os.path.dirname(rapidocr.__file__)
    for sub in ["models"]:
        p = os.path.join(pkg, sub)
        if os.path.isdir(p):
            print("模型目录 %s:" % sub)
            for root, dirs, files in os.walk(p):
                rel = os.path.relpath(root, p)
                fs = [f for f in files if not f.endswith((".pyc",))]
                if fs:
                    print("   %-28s %s" % (rel, fs[:6]))
except Exception:
    traceback.print_exc()
    sys.exit(1)
