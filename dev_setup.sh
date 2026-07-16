# ═══════════════════════════════════════════════════════════════
# Agemini Framework — Adicionando ao PYTHONPATH
# ═══════════════════════════════════════════════════════════════
#
# Executar antes de rodar a pipeline para garantir que os
# módulos do Agemini (conectores, modelos) fiquem acessíveis.
#
# Uso:
#   source dev_setup.sh
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Adiciona Agemini ao PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}/agemini_lib:${SCRIPT_DIR}/src:${PYTHONPATH}"

# Ativa venv se existir
if [ -f "${SCRIPT_DIR}/venv/bin/activate" ]; then
    source "${SCRIPT_DIR}/venv/bin/activate"
fi

echo "[*] PYTHONPATH configurado. Agemini acessível como 'import conectores' e 'import modelos'."
echo "[*] src/ acessível como 'import src'."
