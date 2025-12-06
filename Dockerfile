# Usa uma imagem leve do Python 3.13 (Debian-based para facilidade com drivers de áudio)
FROM python:3.13-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# 1. Instala dependências do SISTEMA (FFmpeg, Opus, Compiladores)
# build-essential é necessário para compilar algumas libs de voz
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    libopus-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Copia o arquivo de requisitos e instala as libs Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia o restante do código (seu script .py)
COPY . .

# Comando para rodar o bot (substitua 'main.py' pelo nome do seu arquivo)
CMD ["python", "main.py"]