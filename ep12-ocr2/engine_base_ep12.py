# -*- coding: utf-8 -*-
"""ep12 引擎层：6 个配置实现同一接口，测量代码只面向接口。

接口与 ep11 的 engine_base.py 完全同名同义（OcrEngine / OcrResult /
load / infer / model_dir / model_bytes / settings），这样两期的口径可对照。

为什么不直接 import ep11 的 engine_base：它带 sha256 冻结自证，改它即 FATAL；
且本期要新增 4 个引擎、ep11 只有 3 个。按 skill §4「新写同级 runner」处理：
paddleocr 那段逐字照抄（含两个坑：① 必须先 import paddleocr 再让 paddle 进来，
否则 torch 的 shm.dll 报 WinError 127；② enable_mkldnn=False，本机 oneDNN 报错）。

⚠️ 计时口径：本层的 infer() 只包引擎推理，不含模型加载（load 单独计时）。
   这与 ep11 bench_cell 的 hot 模式一致。
⚠️ glmocr 特殊：Ollama 缓存**按图片记、不按 prompt 记**，同图重发会命中缓存
   （实测 19.3s → 6.77s）。所以它的 infer() 内部每次先卸载再推理，
   否则 n=3 会全部命中缓存、中位数被严重低估且零报错。
"""
import json
import os
import re
import time
import urllib.request


class OcrResult:
    def __init__(self, text="", lines=None, err="", extra=None):
        self.text = text
        self.lines = lines or []
        self.err = err
        self.extra = extra or {}


class OcrEngine:
    name = "base"

    def __init__(self, model_root="D:/models/ep12-ocr2"):
        self.model_root = model_root
        self._impl = None

    def load(self):
        raise NotImplementedError

    def infer(self, img_path):
        raise NotImplementedError

    def unload(self):
        self._impl = None

    def model_bytes(self):
        raise NotImplementedError

    def model_dir(self):
        raise NotImplementedError

    def settings(self):
        return {"engine": self.name}


def _dir_bytes(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.islink(fp):
                continue
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def _group_lines(items):
    """照抄 ep11 engine_base._group_lines：items=[(y_center, x_min, text)]。

    判据唯一实现 —— SimdPaddleOCR(C#) 只吐原始坐标，也走这个函数分组。
    """
    if not items:
        return []
    items = sorted(items, key=lambda t: t[0])
    lines = []
    cur = [items[0]]
    ys = [items[0][0]]
    for it in items[1:]:
        if abs(it[0] - sum(ys) / len(ys)) <= 14:
            cur.append(it)
            ys.append(it[0])
        else:
            lines.append(" ".join(t[2] for t in sorted(cur, key=lambda t: t[1])))
            cur = [it]
            ys = [it[0]]
    lines.append(" ".join(t[2] for t in sorted(cur, key=lambda t: t[1])))
    return lines


def _rm(*paths):
    """删临时文件，失败不抛（临时文件本就该静默清理）。"""
    for q in paths:
        try:
            os.remove(q)
        except OSError:
            pass


def _items_from_boxes(res):
    """RapidOCR(RapidOCRLite 5.0.0a15) 结果 → [(y_center, x_min, text)]。

    ⚠️ 不能照抄 ep11 的 `res, elapse = ocr(img)` —— 那是 rapidocr_onnxruntime
    1.4.4 的 tuple API。RapidOCRLite 5.0.0a15 返回单个 `RapidOCROutput` 对象，
    解包会抛 `TypeError: cannot unpack non-iterable RapidOCROutput object`，
    而这个错发生在 infer() 内部、引擎已跑完推理，耗时数字看着正常、文本却是空的。
    真实属性（经 dir() 核）：boxes(ndarray N×4×2) / txts(tuple) / scores(tuple)
                            / elapse(float) / elapse_list([det,cls,rec]) /
                            to_json / to_markdown / vis
    """
    if res is None:
        return []
    boxes = getattr(res, "boxes", None)
    txts = getattr(res, "txts", None)
    if boxes is None or txts is None:
        return []
    items = []
    for box, txt in zip(boxes, txts):
        ys = [float(p[1]) for p in box]
        xs = [float(p[0]) for p in box]
        items.append((sum(ys) / len(ys), min(xs), txt))
    return items


class RapidOcrLiteEngine(OcrEngine):
    """RapidOCRLite（RapidAI）。tier = medium（与 PaddleOCR 对齐）或 lite。

    ⚠️ 默认档是 small，必须显式设 medium，否则比的是两个不同大小的模型。
    """
    # 对齐 PaddleOCR predict() 运行时实际检测参数（取自它的 text_det_params 字段）。
    # 三栈默认参数本不同（box_thresh 0.6/0.5/0.45、unclip 1.5/1.6/1.4），
    # 不对齐时 book_02 检出 87/102/27 框 —— 那个差距是参数造成的，不是栈造成的。
    # 对齐后实测 book_02 框数：PaddleOCR 87 / RCL 80 / Simd 91，同一量级。
    ALIGN_DET = {
        "Det.box_thresh": 0.6,
        "Det.thresh": 0.3,
        "Det.unclip_ratio": 1.5,
    }

    def __init__(self, model_root="D:/models/ep12-ocr2", tier="medium",
                 align_det=True):
        super().__init__(model_root)
        self.tier = tier
        self.align_det = align_det
        self.name = "rapidocrlite-%s%s" % (tier, "" if align_det else "-raw")

    def load(self):
        from rapidocr import RapidOCR
        root = os.path.join(self.model_root, "rapidocr")
        params = {
            "Global.model_root_dir": root,
            "Det.lang_type": "ch",
            "Rec.lang_type": "ch",
        }
        if self.tier in ("medium", "small"):
            # 同一条 PP-OCRv6 管线，只换权重大小。small 的 onnx 已随 medium 一并下载。
            params["Det.model_type"] = self.tier
            params["Rec.model_type"] = self.tier
        # tier == "lite" 时不设 model_type，走包内置 lite 配置（5 件套，另一条流水线）
        if self.align_det:
            params.update(self.ALIGN_DET)
        self._impl = RapidOCR(params=params)
        self._model_root = root

    def infer(self, img_path):
        try:
            res = self._impl(img_path)
        except Exception as e:
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        items = _items_from_boxes(res)
        lines = _group_lines(items)
        # RapidOCROutput.elapse = float（总耗时）；elapse_list = [det, cls, rec]
        return OcrResult(text="\n".join(lines), lines=lines, extra={
            "elapse": getattr(res, "elapse", None),
            "elapse_list": getattr(res, "elapse_list", None),
            "n_boxes": len(items)})

    def model_dir(self):
        return self._model_root

    def model_bytes(self):
        return _dir_bytes(self._model_root)

    def settings(self):
        import rapidocr
        d = {"engine": self.name, "backend": "onnxruntime (RapidOCRLite C++/Python)",
             "rapidocr_version": getattr(rapidocr, "__version__", "?"),
             "tier": self.tier, "lang_type": "ch",
             "det_params_aligned_to_paddleocr": self.align_det}
        if self.align_det:
            d["aligned_det"] = dict(self.ALIGN_DET)
        return d


class PaddleOcrEngine(OcrEngine):
    """PaddleOCR 3.7.0（百度）。照抄 ep11，含两个坑。

    坑 1：必须先 import paddleocr 再让 paddle 进来 —— 反过来会在 torch 的
          shm.dll 上报 WinError 127（ep11 README 记录）。
    坑 2：enable_mkldnn=False —— 本机 oneDNN 推理报 Paddle 内部错误。
    """
    name = "paddleocr"

    def load(self):
        import paddleocr
        from paddleocr import PaddleOCR
        self._paddleocr_mod = paddleocr
        self._impl = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="cpu",
            enable_mkldnn=False,
        )

    def infer(self, img_path):
        try:
            preds = self._impl.predict(img_path)
        except Exception as e:
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        items = []
        try:
            for res in preds:
                polys = res.get("rec_polys", [])
                recs = res.get("rec_texts", [])
                for poly, txt in zip(polys, recs):
                    xs = [p[0] for p in poly]
                    ys = [p[1] for p in poly]
                    items.append((sum(ys) / len(ys), min(xs), txt))
        except Exception as e:
            return OcrResult(err="parse: %s: %s" % (type(e).__name__, e))
        lines = _group_lines(items)
        return OcrResult(text="\n".join(lines), lines=lines,
                         extra={"n_boxes": len(items)})

    def model_dir(self):
        return os.path.expanduser("~/.paddlex/official_models")

    def model_bytes(self):
        return _dir_bytes(self.model_dir())

    def settings(self):
        import paddleocr
        return {"engine": self.name, "backend": "paddlepaddle",
                "paddleocr": getattr(paddleocr, "__version__", "?"),
                "models": "PP-OCRv6 det+rec (paddlex 缓存)",
                "enable_mkldnn": False}


class EasyOcrEngine(OcrEngine):
    """EasyOCR（Jaided AI）。纯 PyTorch，参照行（不同权重，不进 A 组排名）。"""
    name = "easyocr"

    def load(self):
        import easyocr
        self._impl = easyocr.Reader(["ch_sim", "en"], gpu=False,
                                    verbose=False, quantize=False)

    def infer(self, img_path):
        try:
            # detail=1 返回 (bbox, text, conf)
            res = self._impl.readtext(img_path, detail=1, paragraph=False)
        except Exception as e:
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        items = []
        for bbox, txt, _conf in res:
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            items.append((sum(ys) / len(ys), min(xs), txt))
        lines = _group_lines(items)
        return OcrResult(text="\n".join(lines), lines=lines,
                         extra={"n_boxes": len(items)})

    def model_dir(self):
        d = os.path.expanduser("~/.EasyOCR/model")
        return d if os.path.isdir(d) else os.path.expanduser("~/.EasyOCR")

    def model_bytes(self):
        return _dir_bytes(self.model_dir())

    def settings(self):
        import easyocr, torch
        return {"engine": self.name, "backend": "torch-cpu",
                "easyocr": getattr(easyocr, "__version__", "?"),
                "torch": torch.__version__, "lang": ["ch_sim", "en"],
                "quantize": False, "gpu": False}


class SimdPaddleOcrEngine(OcrEngine):
    """SimdPaddleOCR（sdcb，纯 C#）。走 SimdBench 子进程。

    为什么不进程内调用：它是 .NET 程序集，Python 侧只能起子进程。
    这意味着它的 load 计时口径 = .NET 进程启动 + 模型加载，
    与 Python 引擎的"进程内 load"**不可横比**（方案 §4.1 已注明）。
    """
    def __init__(self, model_root="D:/models/ep12-ocr2", profile="controlled"):
        super().__init__(model_root)
        self.profile = profile
        self.name = "simdpaddleocr-%s" % profile
        self._exe = (r"D:/study/ai-jms/ep12-ocr2-venvs/simd-test/"
                     r"SimdBench/bin/Release/net10.0/SimdBench.dll")
        self._tmp = r"D:/study/ai-jms/ep12-ocr2-venvs/_simd_tmp"
        os.makedirs(self._tmp, exist_ok=True)

    def load(self):
        self._impl = True   # 占位，表示"已就绪"

    def infer(self, img_path):
        import subprocess
        man = os.path.join(self._tmp, "manifest_%s.txt" % os.getpid())
        out = os.path.join(self._tmp, "out_%s.json" % os.getpid())
        with open(man, "w", encoding="utf-8") as f:
            f.write(img_path + "\n")
        env = dict(os.environ,
                   DOTNET_CLI_TELEMETRY_OPTOUT="1",
                   DOTNET_CLI_HOME=r"D:/study/dotnet",
                   NUGET_PACKAGES=r"D:/d/study/dotnet/nuget")
        try:
            r = subprocess.run(
                [r"D:/study/dotnet/dotnet.exe", self._exe,
                 "--manifest", man, "--profile", self.profile,
                 "--runs", "1", "--warmup", "0", "--out", out],
                env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=300)
        except Exception as e:
            _rm(man)
            return OcrResult(err="%s: %s" % (type(e).__name__, e))

        # ⚠️ 只在读完结果之后才删 out —— 曾把删除放进 finally，导致
        #    "先删文件、再检查文件存在"，必然报"simdbench 无输出"，
        #    而推理其实成功了（median 有值、文本为空），是个自造的假故障。
        if not os.path.exists(out):
            _rm(man)
            return OcrResult(err="simdbench 无输出: stdout=%r stderr=%r" % (
                (r.stdout or "")[-200:], (r.stderr or "")[-200:]))
        try:
            d = json.loads(open(out, encoding="utf-8-sig").read())
        except Exception as e:
            _rm(man, out)
            return OcrResult(err="json: %s" % e)
        _rm(man, out)
        if d.get("load_err"):
            return OcrResult(err="load: " + d["load_err"])
        im = (d.get("images") or [{}])[0]
        if im.get("err"):
            return OcrResult(err=im["err"])
        items = [(it[0], it[1], str(it[2])) for it in (im.get("raw_items") or [])]
        lines = _group_lines(items)
        return OcrResult(text="\n".join(lines), lines=lines,
                         extra={"n_boxes": len(items),
                                "t_infers_csharp": im.get("t_infers"),
                                "effective_line_worker_count":
                                    d.get("effective_line_worker_count")})

    def model_dir(self):
        return os.path.join(self.model_root, "simd")

    def model_bytes(self):
        return _dir_bytes(self.model_dir())

    def settings(self):
        return {"engine": self.name, "backend": "SimdPaddleOCR 2.0.0 (.NET 10, 纯 C#)",
                "profile": self.profile,
                "bundle": "PP-OCRv6_medium (Sdcb.SimdPaddleOCR.Models.ChineseV6Medium 1.0.0)",
                "note": "load 计时含 .NET 进程启动，与 Python 引擎不可横比"}


class GlmOcrEngine(OcrEngine):
    """GLM-OCR（智谱 zai-org）0.9B，经 Ollama 本地推理。

    ⚠️ 三条已实测确认的口径（缺一条数据就废，且零报错）：
    1. 缓存按图片记、不按 prompt 记 → 每次 infer 前必须卸载模型
    2. 内存采样必须从 ollama.exe serve 递归整棵子进程树（推理在 llama-server.exe，
       按进程名匹配会低估 83 倍）
    3. 时间按 load / prefill / eval 三段拆（prefill 占 72.4%）
    """
    name = "glmocr"
    API = "http://127.0.0.1:11434"

    def load(self):
        self._impl = True

    def _post(self, path, payload, timeout=900):
        req = urllib.request.Request(
            self.API + path, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _unload(self):
        """卸载：POST /api/generate 传 keep_alive=0。

        ⚠️ CLI 的 `ollama unload` 在 0.40.11 不存在（报 unknown command 但退出码仍是 0）。
        ⚠️ 判卸载要用 /api/ps（列已加载），不能用 /api/tags（列已下载，永远命中）。
        """
        try:
            self._post("/api/generate",
                       {"model": "glm-ocr", "prompt": "", "keep_alive": 0},
                       timeout=120)
        except Exception:
            pass
        # 轮询确认真卸载
        for _ in range(30):
            try:
                ps = self._post("/api/ps", {}, timeout=30)
                if not ps.get("models"):
                    return True
            except Exception:
                return True
            time.sleep(0.5)
        return False

    def infer(self, img_path):
        import base64
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        self._unload()                       # ← 关键：防按图缓存污染
        t0 = time.time()
        try:
            r = self._post("/api/generate", {
                "model": "glm-ocr",
                "prompt": "OCR the document in the image. "
                          "Output only the recognized text, no explanation.",
                "images": [b64],
                "stream": False,
                "options": {"temperature": 0},
            }, timeout=1200)
        except Exception as e:
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        wall = time.time() - t0
        txt = r.get("response", "")
        # ⚠️ Ollama 的 /api/generate 把 load_duration / prompt_eval_count /
        #    prompt_eval_duration / eval_count / eval_duration / total_duration
        #    放在**响应顶层**；`timings` 子对象是 OpenAI 兼容接口的格式，
        #    用原生 /api/generate 时它不存在 → 只查 timings 会得到全 null/0，
        #    而这个错零报错，看起来像"没拆出三段"。两处都查。
        td = {}
        for k in ("load_duration", "prompt_eval_count", "prompt_eval_duration",
                  "eval_count", "eval_duration", "total_duration"):
            if k in r:
                td[k] = r[k]
            elif isinstance(r.get("timings"), dict) and k in r["timings"]:
                td[k] = r["timings"][k]
        lines = [t for t in str(txt).split("\n") if t.strip()]
        return OcrResult(text=str(txt), lines=lines, extra={
            "wall_s": wall,
            "load_duration_s": round((td.get("load_duration") or 0) / 1e9, 4),
            "prompt_eval_count": td.get("prompt_eval_count"),
            "prompt_eval_duration_s": round((td.get("prompt_eval_duration") or 0) / 1e9, 4),
            "eval_count": td.get("eval_count"),
            "eval_duration_s": round((td.get("eval_duration") or 0) / 1e9, 4),
            "total_duration_s": round((td.get("total_duration") or 0) / 1e9, 4),
            "model": r.get("model"),
        })

    def unload(self):
        self._unload()
        self._impl = None

    def model_dir(self):
        return r"D:/models/ollama"

    def model_bytes(self):
        return _dir_bytes(self.model_dir())

    def settings(self):
        return {"engine": self.name, "backend": "Ollama (glm-ocr, CPU)",
                "params": "0.9B", "api_mode": "local",
                "cache_note": "按图片缓存 → 每次计时前卸载（keep_alive=0）",
                "maas_upload": False}


class LightOnOcrEngine(OcrEngine):
    """LightOnOCR-3 0.8B（LightOn 出品，经 maternion 社区 GGUF 转到 Ollama）。

    ⚠️ 与 GlmOcrEngine 走**完全相同**的路径（卸载→推理→三段计时→顶层取值），
       只换模型名。这样两者的耗时/内存/上下文数字才可直接对照。
    ⚠️ 量化与 GLM-OCR 不同：本模型 Q8_0（1.02 GB），GLM-OCR 是 F16（2.66 GB）。
       正文必须标注，否则"谁快谁慢"会被误读成纯架构差异。
    ⚠️ 权重来源是社区转换（发布者 maternion），非 LightOn 官方发布在 Ollama；
       授权 Apache 2.0 可商用，但来源需在正文注明。
    """
    name = "lightonocr"
    API = "http://127.0.0.1:11434"
    MODEL = "maternion/LightOnOCR-3:0.8b"

    def load(self):
        self._impl = True

    def _post(self, path, payload, timeout=900):
        req = urllib.request.Request(
            self.API + path, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _unload(self):
        try:
            self._post("/api/generate",
                       {"model": self.MODEL, "prompt": "", "keep_alive": 0},
                       timeout=120)
        except Exception:
            pass
        for _ in range(30):
            try:
                ps = self._post("/api/ps", {}, timeout=30)
                if not ps.get("models"):
                    return True
            except Exception:
                return True
            time.sleep(0.5)
        return False

    def infer(self, img_path):
        import base64
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        self._unload()                       # ← 关键：防按图缓存污染
        t0 = time.time()
        try:
            r = self._post("/api/generate", {
                "model": self.MODEL,
                "prompt": "OCR the document in the image. "
                          "Output only the recognized text, no explanation.",
                "images": [b64],
                "stream": False,
                "options": {"temperature": 0},
            }, timeout=1200)
        except Exception as e:
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        wall = time.time() - t0
        # ⚠️ LightOnOCR-3 的关键行为差异（2026-10-26 实测）：
        #   它把识别结果写在 **thinking** 字段里，`response` 是空串。
        #   GLM-OCR 写在 response，所以直接读 response 会得到"生成了 812 个 token
        #   却一个字没识别"的假象，且**零报错**。两处都要查，response 优先。
        txt = r.get("response", "") or r.get("thinking", "") or ""
        src_field = "response" if r.get("response") else (
            "thinking" if r.get("thinking") else "none")
        # 去掉开头的 markdown 图片占位 `![image](xxx.png)` —— 它是模型输出的
        # 伪影而非识别内容，留着会以 "imageimage_1png" 形式污染 CER 分子。
        txt = re.sub(r"^\s*!\[[^\]]*\]\([^)]*\)\s*", "", str(txt), count=1)
        td = {}
        for k in ("load_duration", "prompt_eval_count", "prompt_eval_duration",
                  "eval_count", "eval_duration", "total_duration"):
            if k in r:
                td[k] = r[k]
            elif isinstance(r.get("timings"), dict) and k in r["timings"]:
                td[k] = r["timings"][k]
        lines = [t for t in str(txt).split("\n") if t.strip()]
        return OcrResult(text=str(txt), lines=lines, extra={
            "wall_s": wall,
            "output_field": src_field,
            "load_duration_s": round((td.get("load_duration") or 0) / 1e9, 4),
            "prompt_eval_count": td.get("prompt_eval_count"),
            "prompt_eval_duration_s": round((td.get("prompt_eval_duration") or 0) / 1e9, 4),
            "eval_count": td.get("eval_count"),
            "eval_duration_s": round((td.get("eval_duration") or 0) / 1e9, 4),
            "total_duration_s": round((td.get("total_duration") or 0) / 1e9, 4),
            "model": r.get("model"),
        })

    def unload(self):
        self._unload()
        self._impl = None

    def model_dir(self):
        return r"D:/models/ollama"

    def model_bytes(self):
        return _dir_bytes(self.model_dir())

    def settings(self):
        return {"engine": self.name, "backend": "Ollama (LightOnOCR-3 0.8b, CPU)",
                "params": "0.8B", "api_mode": "local", "quant": "Q8_0",
                "weight_source": "maternion 社区 GGUF 转换（非 LightOn 官方发布）",
                "license": "Apache-2.0",
                "cache_note": "按图片缓存 → 每次计时前卸载（keep_alive=0）",
                "output_field_note": "结果写在 thinking 字段（response 为空），与 GLM-OCR 不同",
                "maas_upload": False}


ENGINES = {
    "rapidocrlite-medium": lambda: RapidOcrLiteEngine(tier="medium"),
    # small：与 medium 同管线（PP-OCRv6 det+rec）、同检测参数对齐，只换权重大小。
    # 用途是回答"降一档位省多少时间/内存、丢多少准确率"。
    "rapidocrlite-small":  lambda: RapidOcrLiteEngine(tier="small", align_det=True),
    "rapidocrlite-lite":   lambda: RapidOcrLiteEngine(tier="lite"),
    "paddleocr":           PaddleOcrEngine,
    "easyocr":             EasyOcrEngine,
    "simdpaddleocr":       lambda: SimdPaddleOcrEngine(profile="controlled"),
    "simdpaddleocr-default": lambda: SimdPaddleOcrEngine(profile="default"),
    "glmocr":              GlmOcrEngine,
    # LightOnOCR-3 0.8B：与 glmocr 同走 Ollama、同卸载口径、同 prompt，
    # 只换模型名 → 两者的耗时/内存/上下文可直接对照。
    "lightonocr":          LightOnOcrEngine,
}


def make_engine(name):
    if name not in ENGINES:
        raise SystemExit("unknown engine: " + name + "  可选: " + ", ".join(sorted(ENGINES)))
    return ENGINES[name]()
