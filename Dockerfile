FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

COPY . .

# expõe 8080 (opcional, mas ajuda na leitura)
EXPOSE 8080

# usa a porta da ENV PORT, ou 8080 se não definida
CMD ["sh","-c","gunicorn -b 0.0.0.0:${PORT:-8080} processa_imagem:app"]
