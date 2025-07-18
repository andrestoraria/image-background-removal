import os
from io import BytesIO

from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import cv2
from rembg import remove

app = Flask(__name__)
CORS(app)  # libera chamadas cross-origin do seu frontend

# Parâmetros configuráveis via env vars
SHADOW_BLUR_RADIUS = int(os.getenv("SHADOW_BLUR_RADIUS", "25"))
SHADOW_OPACITY     = float(os.getenv("SHADOW_OPACITY", "0.4"))
THRESHOLD_SOMBRA   = int(os.getenv("THRESHOLD_SOMBRA", "50"))
FUNDO_PATH         = os.getenv("FUNDO_PATH", None)  # se quiser usar imagem de fundo personalizada

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

def processa_imagem(img_bytes: bytes) -> bytes:
    original_pil = Image.open(BytesIO(img_bytes)).convert("RGBA")
    w, h = original_pil.size

    # recorta o sujeito
    subject_pil = remove(original_pil)

    # pra detectar sombra original
    cv_img = cv2.cvtColor(np.array(original_pil), cv2.COLOR_RGBA2BGRA)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGRA2GRAY)
    _, bin_mask = cv2.threshold(gray, THRESHOLD_SOMBRA, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((5,5), np.uint8)
    bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_OPEN, kernel)

    # decide se há sombra original
    contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    has_shadow = any(cv2.contourArea(c) > (w*h*0.01) for c in contours)

    if has_shadow:
        b = SHADOW_BLUR_RADIUS if SHADOW_BLUR_RADIUS%2==1 else SHADOW_BLUR_RADIUS+1
        m = cv2.GaussianBlur(bin_mask, (b,b), 0)
        mask_pil = Image.fromarray(m).convert("L")
        mask_pil = ImageOps.invert(mask_pil)
        mask_pil = Image.eval(mask_pil, lambda px: int(px * SHADOW_OPACITY))
    else:
        alpha = subject_pil.split()[-1]
        shadow = Image.new("L", (w,h), 0)
        dx, dy = int(w*0.02), int(h*0.05)
        shadow.paste(alpha, (dx, dy))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR_RADIUS))
        mask_pil = Image.eval(shadow, lambda px: int(px * SHADOW_OPACITY))

    # cria fundo
    if FUNDO_PATH:
        try:
            bg = Image.open(FUNDO_PATH).convert("RGBA").resize((w,h), Image.LANCZOS)
        except:
            bg = Image.new("RGBA", (w,h), (255,255,255,255))
    else:
        bg = Image.new("RGBA", (w,h), (255,255,255,255))

    # compõe sombra
    shadow_layer = Image.new("RGBA", (w,h), (0,0,0,0))
    black = Image.new("RGBA", (w,h), (0,0,0,255))
    shadow_layer = Image.composite(black, shadow_layer, mask_pil)

    # compõe tudo
    out = Image.alpha_composite(bg, shadow_layer)
    out = Image.alpha_composite(out, subject_pil)

    buf = BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

@app.route("/api/remocao-fundo", methods=["POST"])
def remocao_fundo():
    if "file" not in request.files:
        return {"error":"No file part"}, 400
    f = request.files["file"]
    if f.filename == "":
        return {"error":"No selected file"}, 400

    try:
        data = f.read()
        result = processa_imagem(data)
        return send_file(BytesIO(result), mimetype="image/png")
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    # quando for rodar local (fora do Docker/Railway):
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=True)
