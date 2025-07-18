import os
from io import BytesIO

from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import cv2
from rembg import remove

app = Flask(__name__)
CORS(app)

SHADOW_BLUR_RADIUS = int(os.getenv("SHADOW_BLUR_RADIUS", "25"))
SHADOW_OPACITY     = float(os.getenv("SHADOW_OPACITY", "0.4"))
THRESHOLD_SOMBRA   = int(os.getenv("THRESHOLD_SOMBRA", "50"))
FUNDO_PATH         = os.getenv("FUNDO_PATH", None)

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

def processa_imagem(img_bytes: bytes) -> bytes:
    original_pil = Image.open(BytesIO(img_bytes)).convert("RGBA")
    w, h = original_pil.size

    subject_pil = remove(original_pil)

    cv_img    = cv2.cvtColor(np.array(original_pil), cv2.COLOR_RGBA2BGRA)
    gray      = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2GRAY)
    _, bin_m  = cv2.threshold(gray, THRESHOLD_SOMBRA, 255, cv2.THRESH_BINARY_INV)
    bin_m     = cv2.morphologyEx(bin_m,
                                 cv2.MORPH_OPEN,
                                 np.ones((5,5),np.uint8))
    ctrs, _   = cv2.findContours(bin_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    has_orig  = any(cv2.contourArea(c) > (w*h*0.01) for c in ctrs)

    if has_orig:
        blur = SHADOW_BLUR_RADIUS if SHADOW_BLUR_RADIUS % 2 else SHADOW_BLUR_RADIUS+1
        mcv  = cv2.GaussianBlur(bin_m, (blur, blur), 0)
        mask = Image.fromarray(mcv).convert("L")
        mask = ImageOps.invert(mask)
        mask = Image.eval(mask, lambda x: int(x*SHADOW_OPACITY))
    else:
        alpha = subject_pil.split()[-1]
        mask  = Image.new("L", (w,h), 0)
        ox, oy = int(w*0.02), int(h*0.05)
        mask.paste(alpha, (ox,oy))
        mask = mask.filter(ImageFilter.GaussianBlur(SHADOW_BLUR_RADIUS))
        mask = Image.eval(mask, lambda x: int(x*SHADOW_OPACITY))

    if FUNDO_PATH:
        try:
            bg = Image.open(FUNDO_PATH).convert("RGBA").resize((w,h), Image.LANCZOS)
        except:
            bg = Image.new("RGBA",(w,h),(255,255,255,255))
    else:
        bg = Image.new("RGBA",(w,h),(255,255,255,255))

    shadow_layer = Image.new("RGBA",(w,h),(0,0,0,0))
    black        = Image.new("RGBA",(w,h),(0,0,0,255))
    shadow_layer = Image.composite(black, shadow_layer, mask)

    comp = Image.alpha_composite(bg, shadow_layer)
    comp = Image.alpha_composite(comp, subject_pil)

    out = BytesIO()
    comp.save(out, format="PNG")
    out.seek(0)
    return out.getvalue()

@app.route("/api/remocao-fundo", methods=["POST"])
def remocao_fundo():
    if "file" not in request.files:
        return "No file part", 400
    f = request.files["file"]
    if not f.filename:
        return "No selected file", 400

    try:
        result = processa_imagem(f.read())
        return send_file(BytesIO(result),
                         mimetype="image/png",
                         as_attachment=False,
                         download_name="result.png")
    except Exception as e:
        return str(e), 500
