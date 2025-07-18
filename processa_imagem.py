import os
from io import BytesIO

from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import cv2
from rembg import remove

app = Flask(__name__)
CORS(app)  # Habilita CORS para chamadas diretas do navegador

# Parâmetros configuráveis via variáveis de ambiente
SHADOW_BLUR_RADIUS = int(os.getenv("SHADOW_BLUR_RADIUS", "25"))
SHADOW_OPACITY = float(os.getenv("SHADOW_OPACITY", "0.4"))
THRESHOLD_SOMBRA = int(os.getenv("THRESHOLD_SOMBRA", "50"))
FUNDO_PATH = os.getenv("FUNDO_PATH", None)  # Caminho para imagem de fundo ou None para branco

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200

def processa_imagem(img_bytes: bytes) -> bytes:
    """
    Remove o fundo de uma imagem, extrai ou gera sombra,
    e compõe o resultado sobre um novo fundo.
    Retorna o PNG resultante em bytes.
    """
    # Carrega a imagem original em PIL
    original_pil = Image.open(BytesIO(img_bytes)).convert("RGBA")
    width, height = original_pil.size

    # Gera o recorte do sujeito com rembg
    subject_pil = remove(original_pil)

    # Converte PIL → OpenCV para processar sombras
    original_cv = cv2.cvtColor(np.array(original_pil), cv2.COLOR_RGBA2BGRA)
    gray_cv = cv2.cvtColor(original_cv, cv2.COLOR_BGRA2GRAY)

    # Isola pixels escuros como potencial sombra
    _, shadow_bin = cv2.threshold(
        gray_cv,
        THRESHOLD_SOMBRA,
        255,
        cv2.THRESH_BINARY_INV
    )
    kernel = np.ones((5, 5), np.uint8)
    shadow_bin = cv2.morphologyEx(shadow_bin, cv2.MORPH_OPEN, kernel)

    # Verifica se há sombra original significativa
    contours, _ = cv2.findContours(
        shadow_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    has_original_shadow = any(
        cv2.contourArea(c) > (width * height * 0.01) for c in contours
    )

    # Cria máscara de sombra final (PIL L)
    if has_original_shadow:
        # Usa a sombra detectada
        blur = SHADOW_BLUR_RADIUS if SHADOW_BLUR_RADIUS % 2 == 1 else SHADOW_BLUR_RADIUS + 1
        mask_cv = cv2.GaussianBlur(shadow_bin, (blur, blur), 0)
        mask_pil = Image.fromarray(mask_cv).convert("L")
        mask_pil = ImageOps.invert(mask_pil)
        mask_pil = Image.eval(mask_pil, lambda x: int(x * SHADOW_OPACITY))
    else:
        # Gera sombra sintética a partir da silhueta
        subject_alpha = subject_pil.split()[-1]
        shadow_pil = Image.new("L", (width, height), 0)
        offset_x = int(width * 0.02)
        offset_y = int(height * 0.05)
        shadow_pil.paste(subject_alpha, (offset_x, offset_y))
        shadow_pil = shadow_pil.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR_RADIUS))
        shadow_pil = Image.eval(shadow_pil, lambda x: int(x * SHADOW_OPACITY))
        mask_pil = shadow_pil

    # Monta o fundo de saída
    if FUNDO_PATH:
        try:
            background = Image.open(FUNDO_PATH).convert("RGBA")
            background = background.resize((width, height), Image.LANCZOS)
        except FileNotFoundError:
            background = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    else:
        background = Image.new("RGBA", (width, height), (255, 255, 255, 255))

    # Compoe sombra sobre o fundo
    shadow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if mask_pil:
        black = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        shadow_layer = Image.composite(black, shadow_layer, mask_pil)

    comp = Image.alpha_composite(background, shadow_layer)
    comp = Image.alpha_composite(comp, subject_pil)

    # Exporta como PNG para bytes
    out = BytesIO()
    comp.save(out, format="PNG")
    out.seek(0)
    return out.getvalue()

@app.route("/api/remocao-fundo", methods=["POST"])
def remocao_fundo():
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    try:
        img_bytes = file.read()
        result_bytes = processa_imagem(img_bytes)
        return send_file(
            BytesIO(result_bytes),
            mimetype="image/png",
            as_attachment=False,
            download_name="result.png"
        )
    except Exception as e:
        # Em caso de erro interno, devolve status 500 com mensagem
        return str(e), 500

if __name__ == "__main__":
    # Parâmetros locais de teste, se quiser rodar direto
    # export SHADOW_BLUR_RADIUS=30
    # export SHADOW_OPACITY=0.5
    # export THRESHOLD_SOMBRA=60
    # export FUNDO_PATH="/app/default_bg.png"
    app.run(host="0.0.0.0", port=5000, debug=True)
