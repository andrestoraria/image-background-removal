# base leve
FROM python:3.11-slim

WORKDIR /app
COPY . .

# dependências
RUN pip install --no-cache-dir -r requirements.txt

# porta padrão (Railway/Vercel vão injetar outra via ENV)
ENV PORT=8080
EXPOSE 8080

# roda Gunicorn apontando para a variável $PORT
CMD ["gunicorn", "processa_imagem:app", "-b", "0.0.0.0:${PORT}", "--workers=1", "--threads=4"]
