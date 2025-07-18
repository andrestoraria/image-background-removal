# 1) Base Python leve
FROM python:3.11-slim

# 2) Cria /app e copia tudo para lá
WORKDIR /app
COPY . .

# 3) Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# 4) Define porta padrão (vai funcionar localmente e também pegará o PORT injetado pelo Railway)
ENV PORT=8080
EXPOSE 8080

# 5) Usa ENTRYPOINT em modo shell para expandir $PORT
ENTRYPOINT  gunicorn processa_imagem:app \
             --bind 0.0.0.0:$PORT \
             --workers 1 \
             --threads 4
