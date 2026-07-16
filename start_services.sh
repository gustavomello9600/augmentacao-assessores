#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Augmentação de Assessores — Script de inicialização
# ═══════════════════════════════════════════════════════════════
#
# Inicia:
#   1. Serviço Baileys para cada assessor (WhatsApp Web)
#   2. Pipeline Python (quando os serviços estiverem prontos)
#
# Uso:
#   ./start_services.sh           # Inicia Assessor 1 na porta 3100
#   ASSESSORES=2 ./start_services.sh  # Inicia Assessores 1 e 2
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Carrega .env se existir (para variáveis como ASSESSOR_1_*)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

ASSESSORES="${ASSESSORES:-1}"
IFS=',' read -ra LISTA <<< "$ASSESSORES"

echo "╔══════════════════════════════════════════════╗"
echo "║   🚀 AUMENTAÇÃO DE ASSESSORES                 ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Instalar dependências se necessário ──────────────────
if [ ! -d "node_modules" ]; then
    echo "[*] Instalando dependências Node.js..."
    npm install
fi

if [ ! -d "venv" ]; then
    echo "[*] Criando ambiente virtual Python..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# ── Iniciar serviços Baileys ────────────────────────────
echo ""
echo "── Iniciando serviços Baileys ──"

PORTA_BASE=3100
SERVICES_PIDS=()

for i in "${LISTA[@]}"; do
    i_trim=$(echo "$i" | xargs)
    PORTA=$((PORTA_BASE + i_trim - 1))
    SESSION_DIR="${SCRIPT_DIR}/sessions/assessor${i_trim}"

    # Pega o nome do assessor ou usa default
    NOME_VAR="ASSESSOR_${i_trim}_NOME"
    NOME="${!NOME_VAR:-"Assessor ${i_trim}"}"

    echo "  [*] Assessor ${i_trim}: ${NOME} → porta ${PORTA}"

    PORT=${PORTA} \
    ASSESSOR_NOME="${NOME}" \
    SESSION_DIR="${SESSION_DIR}" \
    node baileys_service.js &
    SERVICES_PIDS+=($!)

    # Pequena pausa entre inicializações
    sleep 1
done

echo ""
echo "[*] Serviços Baileys iniciados. Aguardando conexão WhatsApp..."
echo "[*] Se for primeira execução, escaneie o(s) QR Code(s) acima."

# ── Aguardar serviços ficarem saudáveis ──────────────────
echo ""
echo "[*] Verificando saúde dos serviços..."

for i in "${LISTA[@]}"; do
    i_trim=$(echo "$i" | xargs)
    PORTA=$((PORTA_BASE + i_trim - 1))

    ATTEMPTS=0
    MAX_ATTEMPTS=30
    while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
        if curl -s "http://localhost:${PORTA}/health" > /dev/null 2>&1; then
            echo "  [+] Serviço na porta ${PORTA} respondendo."
            break
        fi
        sleep 2
        ATTEMPTS=$((ATTEMPTS + 1))
    done

    if [ $ATTEMPTS -ge $MAX_ATTEMPTS ]; then
        echo "  [!] Timeout aguardando serviço na porta ${PORTA}."
    fi
done

# ── Executar pipeline Python ─────────────────────────────
echo ""
echo "── Executando pipeline ──"
python main.py

# ═══════════════════════════════════════════════════════════
# Limpeza (opcional: descomente para matar serviços ao final)
# ═══════════════════════════════════════════════════════════
# echo ""
# echo "[*] Encerrando serviços Baileys..."
# for pid in "${SERVICES_PID[@]}"; do
#     kill $pid 2>/dev/null || true
# done
# echo "  [+] Serviços encerrados."

echo ""
echo "✅ Finalizado."
