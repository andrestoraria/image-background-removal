# Usamos imagem leve do Debian + Python 3.11
FROM python:3.11-slim

WORKDIR /app

# Copia e instala dependências
COPY requirements.txt .
# Instala libs do sistema necessárias para OpenCV / rembg
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libgl1-mesa-glx \
      libglib2.0-0 \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y build-essential \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# Copia todo o código Python
COPY . .

# Usa a porta que o Railway injeta via var ENV
ENV PORT 8080
EXPOSE 8080

# Ativa o WSGI servidor de produção
# IMPORTANTE: usar shell form para expandir $PORT
CMD gunicorn processa_imagem:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
