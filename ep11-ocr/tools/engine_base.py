# -*- coding: utf-8 -*-
"""ep11 引擎抽象：三个引擎实现同一接口，测量代码只面向接口。"""
import os
import time


class OcrResult:
    def __init__(self, text="", lines=None, err="", extra=None):
        self.text = text
        self.lines = lines or []
        self.err = err
        self.extra = extra or {}


class OcrEngine:
    name = "base"

    def __init__(self, model_root="D:/models/ocr"):
        self.model_root = model_root
        self._impl = None

    # --- 三个引擎都要实现 ---
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
        """口径参数，写进结果，避免事后说不清配置。"""
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
    """items: [(y_center, x1, text)] -> 按 y 聚类成行，行内按 x 排序。"""
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


class RapidOcrEngine(OcrEngine):
    name = "rapidocr"

    def load(self):
        from rapidocr_onnxruntime import RapidOCR
        self._impl = RapidOCR()

    def infer(self, img_path):
        try:
            res, elapse = self._impl(img_path)
        except Exception as e:  # noqa
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        items = []
        for r in (res or []):
            box, txt, score = r[0], r[1], float(r[2])
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            items.append((sum(ys) / 4.0, min(xs), txt))
        lines = _group_lines(items)
        return OcrResult(text="\n".join(lines), lines=lines,
                         extra={"elapse": elapse, "n_boxes": len(items)})

    def model_dir(self):
        import rapidocr_onnxruntime as m
        return os.path.dirname(m.__file__)

    def model_bytes(self):
        return _dir_bytes(self.model_dir())

    def settings(self):
        return {"engine": self.name, "backend": "onnxruntime",
                "models": "PP-OCRv4 det+rec(cls) onnx"}


class PaddleOcrEngine(OcrEngine):
    name = "paddleocr"

    def load(self):
        # 注意：必须先 import paddleocr 再让 paddle 进来。反过来（先 import paddle
        # 再 import paddleocr）会在 torch 的 shm.dll 上报 WinError 127，见 README 坑。
        import paddleocr
        from paddleocr import PaddleOCR
        self._paddleocr_mod = paddleocr
        self._impl = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="cpu",
            enable_mkldnn=False,   # 本机 oneDNN 推理报 Paddle 内部错误，见 README 坑
        )

    def infer(self, img_path):
        try:
            preds = self._impl.predict(img_path)
        except Exception as e:  # noqa
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        items = []
        texts = []
        try:
            for res in preds:
                polys = res.get("rec_polys", [])
                recs = res.get("rec_texts", [])
                for poly, txt in zip(polys, recs):
                    xs = [p[0] for p in poly]
                    ys = [p[1] for p in poly]
                    items.append((sum(ys) / len(ys), min(xs), txt))
                    texts.append(txt)
        except Exception as e:  # noqa
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


class GotOcrEngine(OcrEngine):
    """GOT-OCR2.0 端到端多模态，Apache-2.0，580M 参数。走独立解释器（见 got_venv）。"""
    name = "gotocr"

    def load(self):
        from transformers import AutoModel, AutoTokenizer
        path = os.path.join(self.model_root, "GOT-OCR2-0-CPU")
        self._tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
        self._impl = AutoModel.from_pretrained(
            path, trust_remote_code=True, low_cpu_mem_usage=True,
            device_map="cpu", use_safetensors=True,
            pad_token_id=self._tok.eos_token_id)
        self._impl = self._impl.eval().cpu()

    def infer(self, img_path):
        try:
            txt = self._impl.chat(self._tok, img_path, ocr_type="ocr")
        except Exception as e:  # noqa
            return OcrResult(err="%s: %s" % (type(e).__name__, e))
        lines = [t for t in str(txt).split("\n") if t.strip()]
        return OcrResult(text=str(txt), lines=lines)

    def model_dir(self):
        return os.path.join(self.model_root, "GOT-OCR2-0-CPU")

    def model_bytes(self):
        return _dir_bytes(self.model_dir())

    def settings(self):
        import torch
        return {"engine": self.name, "backend": "torch-cpu",
                "torch": torch.__version__, "params": "580M"}


ENGINES = {
    "rapidocr": RapidOcrEngine,
    "paddleocr": PaddleOcrEngine,
    "gotocr": GotOcrEngine,
}


def make_engine(name):
    if name not in ENGINES:
        raise SystemExit("unknown engine: " + name)
    return ENGINES[name]()
