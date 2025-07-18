# Use uma imagem leve de Python
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Copia só o requirements e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código da sua pasta atual
COPY . .

# Aplique variáveis de ambiente
# Define a PORT padrão (Railway vai sobrescrever essa var se usar outra porta)
ENV PORT=8080

# Informa ao Docker que o container vai escutar nessa porta
EXPOSE 8080

# Comando final: inicia o Gunicorn ligando na porta definida por $PORT
# Supondo que seu flask app esteja em processa_imagem.py e o app se chame "app"
CMD ["gunicorn", "processa_imagem:app", "--bind", "0.0.0.0:${PORT}", "--workers", "1", "--timeout", "120"]
