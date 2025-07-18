import os
from io import BytesIO
from flask import Flask, request, send_file
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import cv2
from rembg import remove

app = Flask(__name__)

# Configurable parameters from environment variables
SHADOW_BLUR_RADIUS = int(os.getenv("SHADOW_BLUR_RADIUS", "25"))
SHADOW_OPACITY = float(os.getenv("SHADOW_OPACITY", "0.4"))
THRESHOLD_SOMBRA = int(os.getenv("THRESHOLD_SOMBRA", "50"))
FUNDO_PATH = os.getenv("FUNDO_PATH", None)

def processa_imagem(img_bytes: bytes) -> bytes:
    original_pil_img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    width, height = original_pil_img.size

    subject_pil_img = remove(original_pil_img)

    original_cv_img = cv2.cvtColor(np.array(original_pil_img), cv2.COLOR_RGBA2BGRA)
    gray_cv_img = cv2.cvtColor(original_cv_img, cv2.COLOR_BGRA2GRAY)
    _, shadow_binary = cv2.threshold(gray_cv_img, THRESHOLD_SOMBRA, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((5,5), np.uint8)
    shadow_binary = cv2.morphologyEx(shadow_binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(shadow_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    has_original_shadow = any(cv2.contourArea(c) > (width * height * 0.01) for c in contours)

    if has_original_shadow:
        shadow_mask_cv = cv2.GaussianBlur(shadow_binary, (SHADOW_BLUR_RADIUS, SHADOW_BLUR_RADIUS), 0)
        shadow_mask_pil = Image.fromarray(shadow_mask_cv).convert("L")
        shadow_mask_pil = ImageOps.invert(shadow_mask_pil)
        shadow_mask_pil = Image.eval(shadow_mask_pil, lambda x: int(x * SHADOW_OPACITY))
    else:
        subject_mask = subject_pil_img.split()[-1]
        shadow_pil = Image.new("L", (width, height), 0)
        offset_x = int(width * 0.02)
        offset_y = int(height * 0.05)
        shadow_pil.paste(subject_mask, (offset_x, offset_y))
        shadow_pil = shadow_pil.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR_RADIUS))
        shadow_pil = Image.eval(shadow_pil, lambda x: int(x * SHADOW_OPACITY))
        shadow_mask_pil = shadow_pil

    if FUNDO_PATH:
        try:
            background_pil = Image.open(FUNDO_PATH).convert("RGBA")
            background_pil = background_pil.resize((width, height), Image.LANCZOS)
        except:
            background_pil = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    else:
        background_pil = Image.new("RGBA", (width, height), (255, 255, 255, 255))

    shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if shadow_mask_pil:
        black_shadow = Image.new("RGB", (width, height), (0, 0, 0))
        shadow_layer.putalpha(shadow_mask_pil)
        shadow_layer = Image.composite(black_shadow, Image.new("RGB", (width, height), (0,0,0)), shadow_layer)
        shadow_layer.putalpha(shadow_mask_pil)

    final_image = Image.alpha_composite(background_pil, shadow_layer)
    final_image = Image.alpha_composite(final_image, subject_pil_img)

    output_buffer = BytesIO()
    final_image.save(output_buffer, format="PNG")
    output_buffer.seek(0)
    return output_buffer.getvalue()

@app.route("/api/remocao-fundo", methods=["POST"])
def remocao_fundo():
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400
    img_bytes = file.read()
    out_bytes = processa_imagem(img_bytes)
    return send_file(BytesIO(out_bytes), mimetype="image/png")

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
