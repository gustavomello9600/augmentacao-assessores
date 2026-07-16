# ── Stage 1: Base com Python 3.11 + Node.js ──
FROM python:3.11-slim

# Instalar Node.js 22.x (npm incluso)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Dependências Python ──────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Dependências Node.js (Baileys) ──────────
COPY package.json package-lock.json ./
RUN npm ci --production

# ── Código da aplicação ─────────────────────
COPY . .

# Scripts executáveis
RUN chmod +x entrypoint.sh main.py

# O entrypoint.sh decodifica a sessão WhatsApp e chama main.py
ENTRYPOINT ["./entrypoint.sh"]
