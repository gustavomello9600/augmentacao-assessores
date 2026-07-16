#!/usr/bin/env python3
"""
Entry point da pipeline de Aumentação de Assessores.

Cada job Cloud Run executa UM assessor, definido por ASSESSOR_PREFIX.
Ex: ASSESSOR_PREFIX=ASSESSOR_2 → usa variáveis ASSESSOR_2_*

Fluxo:
  1. Carrega config do assessor
  2. Inicia Baileys (subprocesso Node.js) — reusa sessão se existir
  3. Executa pipeline (Drive → Sheets → Gemini → WhatsApp)
  4. Encerra Baileys

Uso:
  python main.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agemini_lib"))

from src.config import get_config
from src.whatsapp import BaileysManager
from src.orquestrador import executar


def main():
    config = get_config()

    prefixo = os.environ.get("ASSESSOR_PREFIX", "ASSESSOR_1")
    print("=" * 60)
    print(f"  🚀 AUMENTAÇÃO DE ASSESSORES — {config.nome}")
    print(f"  Prefixo: {prefixo}")
    print("=" * 60)

    # ── Iniciar Baileys ──────────────────────────────
    session_dir = os.path.join(os.path.dirname(__file__), "sessions",
                               prefixo.split("_")[-1])
    manager = BaileysManager(session_dir=session_dir, porta=3100)

    if not manager.iniciar(timeout=45):
        print(f"\n❌ WhatsApp não conectou para {config.nome}.")
        manager.encerrar()
        sys.exit(1)

    # ── Executar pipeline ────────────────────────────
    try:
        executar(config, whatsapp_client=manager.client)
        print(f"\n✅ Pipeline concluída para {config.nome}.")
    except Exception as e:
        print(f"\n❌ [{config.nome}] ERRO: {e}")
        sys.exit(1)
    finally:
        manager.encerrar()


if __name__ == "__main__":
    main()
