FROM python:3.12-slim

WORKDIR /errbot

# Instalar herramientas de compilación y nmap
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    nmap \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["errbot"]