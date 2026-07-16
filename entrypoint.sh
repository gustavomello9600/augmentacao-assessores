#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# entrypoint.sh — Job Cloud Run de Augmentação de Assessores
# ═══════════════════════════════════════════════════════════════
#
# 1. Decodifica a sessão WhatsApp (se fornecida como base64)
# 2. Executa o pipeline Python (que inicia/para o Baileys sozinho)
#
# Variáveis de ambiente esperadas:
#   ASSESSOR_PREFIX=ASSESSOR_1          (qual assessor)
#   ASSESSOR_1_BAILEYS_CREDS_B64=...    (sessão WhatsApp em base64)
#   ASSESSOR_1_GEMINI_API_KEY=...       (chave Gemini)
#   ASSESSOR_1_GOOGLE_CREDENTIALS_JSON=... (service account)
#   ... (demais IDs de Drive/Sheets)
#
# ═══════════════════════════════════════════════════════════════
set -e

PREFIX="${ASSESSOR_PREFIX:-ASSESSOR_1}"
SESSION_DIR="./sessions/${PREFIX##ASSESSOR_}"
CREDS_VAR="${PREFIX}_BAILEYS_CREDS_B64"

echo "╔══════════════════════════════════════════╗"
echo "║   🚀 AUMENTAÇÃO DE ASSESSORES            ║"
echo "║   Prefixo: $PREFIX                       ║"
echo "╚══════════════════════════════════════════╝"

# Decodifica a sessão do WhatsApp (se fornecida)
if [ -n "${!CREDS_VAR}" ]; then
    echo "[entrypoint] Decodificando sessão WhatsApp..."
    mkdir -p "$SESSION_DIR"
    echo "${!CREDS_VAR}" | base64 -d > "$SESSION_DIR/creds.json"
    echo "[entrypoint] ✅ Sessão restaurada."
else
    echo "[entrypoint] ⚠️ Sem sessão WhatsApp. QR code será gerado."
    mkdir -p "$SESSION_DIR"
fi

# Executa pipeline (o Python gerencia o ciclo de vida do Baileys)
echo "[entrypoint] Iniciando pipeline..."
python3 main.py
echo "[entrypoint] ✅ Pipeline concluída."
