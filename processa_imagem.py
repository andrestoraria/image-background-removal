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

# Parâmetros via ENV
SHADOW_BLUR_RADIUS = int(os.getenv("SHADOW_BLUR_RADIUS", "25"))
SHADOW_OPACITY = float(os.getenv("SHADOW_OPACITY", "0.4"))
THRESHOLD_SOMBRA = int(os.getenv("THRESHOLD_SOMBRA", "50"))
FUNDO_PATH = os.getenv("FUNDO_PATH", None)

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

def processa_imagem(img_bytes: bytes) -> BytesIO:
    orig = Image.open(BytesIO(img_bytes)).convert("RGBA")
    w, h = orig.size

    # remove background
    subj = remove(orig)

    # prepara máscara de sombra (OpenCV → PIL)
    cv_img = cv2.cvtColor(np.array(orig), cv2.COLOR_RGBA2BGRA)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2GRAY)
    _, bin_m = cv2.threshold(gray, THRESHOLD_SOMBRA, 255, cv2.THRESH_BINARY_INV)
    bin_m = cv2.morphologyEx(bin_m, cv2.MORPH_OPEN, np.ones((5,5), np.uint8))
    cnts, _ = cv2.findContours(bin_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    has_shadow = any(cv2.contourArea(c) > (w*h*0.01) for c in cnts)

    if has_shadow:
        blur = SHADOW_BLUR_RADIUS if SHADOW_BLUR_RADIUS % 2 else SHADOW_BLUR_RADIUS+1
        m = cv2.GaussianBlur(bin_m, (blur, blur), 0)
        mask = Image.fromarray(m).convert("L")
        mask = ImageOps.invert(mask)
        mask = Image.eval(mask, lambda px: int(px * SHADOW_OPACITY))
    else:
        alpha = subj.split()[-1]
        mask = Image.new("L", (w, h), 0)
        ox, oy = int(w*0.02), int(h*0.05)
        mask.paste(alpha, (ox, oy))
        mask = mask.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR_RADIUS))
        mask = Image.eval(mask, lambda px: int(px * SHADOW_OPACITY))

    # background
    if FUNDO_PATH:
        try:
            bg = Image.open(FUNDO_PATH).convert("RGBA").resize((w, h), Image.LANCZOS)
        except:
            bg = Image.new("RGBA", (w, h), (255,255,255,255))
    else:
        bg = Image.new("RGBA", (w, h), (255,255,255,255))

    # compõe tudo
    shadow_layer = Image.new("RGBA", (w, h), (0,0,0,0))
    black = Image.new("RGBA", (w, h), (0,0,0,255))
    shadow_layer = Image.composite(black, shadow_layer, mask)
    final = Image.alpha_composite(bg, shadow_layer)
    final = Image.alpha_composite(final, subj)

    buf = BytesIO()
    final.save(buf, "PNG")
    buf.seek(0)
    return buf

@app.route("/api/remocao-fundo", methods=["POST"])
def remocao_fundo():
    if "file" not in request.files:
        return "No file part", 400
    f = request.files["file"]
    if f.filename == "":
        return "No selected file", 400
    try:
        img = f.read()
        out = processa_imagem(img)
        return send_file(out, mimetype="image/png")
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=True)
