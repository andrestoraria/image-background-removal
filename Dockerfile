# 1) Base pequeno
FROM python:3.11-slim

WORKDIR /app

# 2) Dependências de SO para OpenCV e libglib/libgl
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 3) Copia requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# 4) Copia o resto do código
COPY . .

# 5) Expõe a porta que o Railway injeta (geralmente 8080)
EXPOSE 8080

# 6) Comando de produção
CMD ["gunicorn", "-b", "0.0.0.0:8080", "processa_imagem:app"]
