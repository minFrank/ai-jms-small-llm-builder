"""TeleOCR 复活实验2：官方图像预处理链（PNG→PIL存PDF 72dpi→PyMuPDF 200dpi渲染→layout）。"""
import sys, os, time, json, io
from PIL import Image, ImageOps

IMG = r"D:/study/ai-jms/ep13-docparse/runs/demo_paddle.png"
OUT_IMG = r"D:/study/ai-jms/ep13-docparse/runs/tele_official_preproc.png"
OUT_JSON = r"D:/study/ai-jms/ep13-docparse/runs/p0_tele_revive2.json"

def official_preprocess(src, dst):
    """复刻 TeleOCR tools: images_bytes_to_pdf_bytes + pdf_page_to_image(dpi=200)"""
    import fitz  # PyMuPDF
    img = Image.open(src)
    img = ImageOps.exif_transpose(img) or img
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PDF")           # 官方: PIL save 默认 72dpi
    pdf_bytes = buf.getvalue()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    zoom = 200 / 72.0                      # 官方: dpi=200 → zoom=2.78
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(dst)
    doc.close()
    return Image.open(dst).size

if __name__ == "__main__":
    size = official_preprocess(IMG, OUT_IMG)
    print("[preproc] 官方链完成 → %s | 尺寸 %s（原 %s）" % (
        OUT_IMG, size, Image.open(IMG).size), flush=True)
