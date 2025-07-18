# --- 1) Imagem base minimalista com Python 3.11 slim
FROM python:3.11-slim

# --- 2) Definir diretório de trabalho
WORKDIR /app

# --- 3) Copiar requirements e instalar dependências de SO+pip
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc \
      libgl1 \
      libglib2.0-0 && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc && \
    rm -rf /var/lib/apt/lists/*

# --- 4) Copiar todo o código para /app
COPY . .

# --- 5) Expor a porta padrão do container (Railway injeta $PORT)
EXPOSE 8080

# --- 6) Comando de inicialização usando shell-form para expandir $PORT
#     Ele vai rodar o Gunicorn atrelado à sua app Flask em processa_imagem:app
CMD gunicorn \
     --bind 0.0.0.0:"${PORT:-8080}" \
     --workers 1 \
     --worker-class sync \
     processa_imagem:app
