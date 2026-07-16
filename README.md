# 🚀 Augmentação de Assessores

Pipeline automatizada de envio de relatórios XPerformance (XP Investimentos) para clientes via WhatsApp, usando IA para personalização.

## Arquitetura

```
augmentacao-assessores/
│
├── main.py                      # Entry point (orquestra todos os assessores)
├── src/
│   ├── config.py                # Config multi-assessor (env vars prefixadas)
│   ├── orquestrador.py          # Pipeline core (Drive → Sheets → Gemini → WhatsApp)
│   └── whatsapp.py              # Cliente HTTP para o serviço Baileys
│
├── baileys_service.js           # WhatsApp Web Gateway (substituto da Z-API)
├── package.json                 # Dependências Node.js (Baileys)
├── agemini_lib/ → ../Agemini    # Framework Agemini (Google Drive, Sheets, Gemini)
│
├── .env.example                 # Template de variáveis de ambiente
├── requirements.txt             # Dependências Python
├── start_services.sh            # Script para iniciar tudo (Baileys + Pipeline)
└── Dockerfile.baileys           # Container para o serviço Baileys
```

## Fluxo

```
Google Drive (PDFs) → Gemini (valida + gera msg) → Google Sheets (PROCV)
                                                        ↓
                                              Baileys (WhatsApp Web)
                                                        ↓
                                                   Cliente 📱
```

## Pré-requisitos

- **Python 3.11+**
- **Node.js 18+** (para o serviço Baileys)
- Conta Google Cloud com APIs habilitadas (Drive, Sheets, Gemini)
- Service Account com acesso às pastas/planilhas do Google Drive

## Instalação

```bash
# 1. Clone o repositório
git clone <repo-url>
cd augmentacao-assessores

# 2. Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Node.js (serviço Baileys)
npm install

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais
```

## Configuração Multi-Assessor

Cada assessor tem variáveis prefixadas. Exemplo para 2 assessores:

```bash
# .env
ASSESSORES_ATIVOS=1,2

# Assessor 1 — João
ASSESSOR_1_NOME="João Silva"
ASSESSOR_1_GEMINI_API_KEY="AIza..."
ASSESSOR_1_GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'
ASSESSOR_1_ID_PASTA_PENDENTES="1KbzH..."
ASSESSOR_1_WHATSAPP_SERVICE_URL="http://localhost:3100"

# Assessor 2 — Maria
ASSESSOR_2_NOME="Maria Oliveira"
ASSESSOR_2_GEMINI_API_KEY="AIza..."
ASSESSOR_2_GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'
ASSESSOR_2_ID_PASTA_PENDENTES="1ABC..."
ASSESSOR_2_WHATSAPP_SERVICE_URL="http://localhost:3101"
```

## Uso

### 1. Iniciar serviço Baileys (WhatsApp Web)

Para cada assessor, inicie uma instância:

```bash
# Terminal 1 — Assessor 1 (porta 3100)
PORT=3100 ASSESSOR_NOME="João Silva" SESSION_DIR="./sessions/assessor1" node baileys_service.js

# Terminal 2 — Assessor 2 (porta 3101)
PORT=3101 ASSESSOR_NOME="Maria Oliveira" SESSION_DIR="./sessions/assessor2" node baileys_service.js
```

Na primeira execução, escaneie o QR Code com o WhatsApp do assessor.

### 2. Executar pipeline

```bash
source venv/bin/activate
python main.py
```

### 3. Usando Docker (serviço Baileys)

```bash
# Construir
docker build -f Dockerfile.baileys -t baileys-service .

# Executar (Assessor 1)
docker run -d \
  --name baileys-assessor1 \
  -p 3100:3100 \
  -e PORT=3100 \
  -e ASSESSOR_NOME="João Silva" \
  -v $(pwd)/sessions/assessor1:/app/baileys_sessions \
  baileys-service
```

## Migração da Z-API para Baileys

| Feature | Z-API (antigo) | Baileys (novo) |
|---------|---------------|-----------------|
| Custo | Pago (por instância) | **Grátis** |
| Infra | API externa (z-api.io) | **Local** (Node.js) |
| Sessão | Gerenciada pela Z-API | **Arquivo local** |
| Envio texto | `POST /send-text` | `POST /send-text` |
| Envio PDF | `POST /send-document/pdf` | `POST /send-document/pdf` |
| Verif. número | `GET /phone-exists/:phone` | `GET /phone-exists/:phone` |

**A API REST é compatível** — mesma estrutura de endpoints, mesma resposta JSON.

## Licença

MIT
