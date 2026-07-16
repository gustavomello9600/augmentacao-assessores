#!/usr/bin/env python3
"""
Teste REAL da pipeline conectando ao Google Drive, Sheets e Docs.

Fluxo completo (idêntico ao orquestrador_v2.py):
  1. BaileysManager → inicia serviço WhatsApp
  2. Autentica Google Drive + Sheets (service account)
  3. Lê personalização do Google Docs
  4. Busca PDFs pendentes na pasta do Drive
  5. PROCV: identifica cliente pelo nome do arquivo na planilha
  6. Valida relatório (PyPDF2 fallback)
  7. Gera mensagem (N-Shot fallback, sem Gemini)
  8. Envia PDF + texto via Baileys
  9. Move PDF para Processados
  10. Registra log na planilha
  11. BaileysManager → encerra serviço

Uso:
  python3 test_pipeline_drive.py
"""

import sys
import os
import re
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dotenv import load_dotenv
load_dotenv()

from src.config import AssessorConfig, get_config
from src.whatsapp import BaileysManager, BaileysClient
from src.orquestrador import (
    obter_servicos_google,
    buscar_relatorios_pendentes,
    descarregar_relatorio,
    mover_arquivo_drive,
    ler_personalizacao_assessor,
    buscar_dados_cliente,
    registrar_log,
    marcar_status_envio,
    atualizar_ultimo_resumo,
)
from gerar_pdf_teste import gerar_pdf_cliente

# Fallback: validação e geração (sem Gemini)
from test_pipeline_v2 import (

    validar_relatorio_ativo as validar_relatorio,
    gerar_mensagem_fallback,
    N_SHOT_EXAMPLES,
)


def main():
    print("=" * 60)
    print("  🚀 PIPELINE REAL — Google Drive + Sheets + Baileys")
    print("=" * 60)

    # ═══ PASSO 0: Carregar config ═══
    print("\n── Carregando configuração ──")
    try:
        config = get_config()
    except Exception as e:
        print(f"  ❌ Erro na config: {e}")
        print("  Execute setup_drive_teste.py primeiro.")
        sys.exit(1)

    print(f"  Assessor: {config.nome}")
    print(f"  Drive Pendentes: {config.id_pasta_pendentes[:20]}...")
    print(f"  Drive Processados: {config.id_pasta_processados[:20]}...")
    print(f"  Planilha: {config.id_planilha_clientes[:20]}...")
    print(f"  Docs: {config.id_doc_personalizacao[:20]}...")
    print(f"  Baileys URL: {config.whatsapp_service_url}")

    # ═══ PASSO 1: Iniciar Baileys ═══
    print(f"\n{'─'*40}")
    print("PASSO 1: Iniciando Baileys (liga → conecta)")
    session_dir = os.path.join(
        os.path.dirname(__file__), "sessions",
        os.environ.get("ASSESSOR_PREFIX", "ASSESSOR_1").split("_")[-1]
    )
    manager = BaileysManager(session_dir=session_dir, porta=3100)

    if not manager.iniciar(timeout=45):
        print("  ❌ WhatsApp não conectou.")
        manager.encerrar()
        sys.exit(1)

    client = manager.client
    print("  ✅ Baileys conectado.")

    # ═══ PASSO 2: Conectar Google ═══
    print(f"\n{'─'*40}")
    print("PASSO 2: Conectando Google Drive + Sheets (service account)")
    try:
        drive_service, sheets_service = obter_servicos_google(config)
        print(f"  ✅ Google autenticado.")
    except Exception as e:
        print(f"  ❌ Erro auth Google: {e}")
        manager.encerrar()
        sys.exit(1)

    # ═══ PASSO 3: Ler personalização ═══
    print(f"\n{'─'*40}")
    print("PASSO 3: Lendo Google Docs de personalização")
    personalizacao = ler_personalizacao_assessor(drive_service, config.id_doc_personalizacao)
    if personalizacao:
        preview = personalizacao[:120].replace('\n', ' ')
        print(f"  ✅ Docs carregado ({len(personalizacao)} chars): {preview}...")
    else:
        print("  ⚠️ Docs vazio ou não encontrado. Seguindo sem personalização extra.")
        personalizacao = ""

    # ═══ PASSO 4: Buscar PDFs pendentes ═══
    print(f"\n{'─'*40}")
    print("PASSO 4: Buscando relatórios PDF no Drive")
    relatorios = buscar_relatorios_pendentes(drive_service, config.id_pasta_pendentes)
    itens = [{'nome': r['name'], 'drive_id': r['id']} for r in relatorios]

    if not itens:
        print("  ❌ Nenhum PDF encontrado na pasta Pendentes.")
        manager.encerrar()
        sys.exit(1)

    print(f"  ✅ {len(itens)} relatório(s) encontrado(s):")
    for item in itens:
        print(f"     📄 {item['nome']}")

    # ═══ PASSO 5-9: Pipeline por relatório ═══
    limite = min(config.envios_por_execucao, len(itens))
    processados = 0

    for item in itens[:limite]:
        nome_arquivo = item['nome']
        drive_id = item['drive_id']

        print(f"\n{'─'*40}")
        print(f"PASSO 5: Processando {nome_arquivo}")

        # 5a. PROCV na planilha
        dados_cliente = buscar_dados_cliente(
            sheets_service,
            config.id_planilha_clientes,
            config.nome_aba_clientes,
            nome_arquivo,
        )

        if not dados_cliente:
            print(f"  ❌ Cliente não encontrado na planilha para '{nome_arquivo}'")
            registrar_log(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_logs, config.nome_aba_clientes,
                nome_arquivo, "Desconhecido", "ERRO", "Cliente nao encontrado"
            )
            continue

        print(f"  ✅ Cliente: {dados_cliente['nome']} | Status: {dados_cliente['status']}")
        print(f"     Telefone: {dados_cliente['telefone']}")
        print(f"     Tom: {dados_cliente['tom_de_voz']}")

        # Verificar pausa
        if dados_cliente.get('status') == 'Envio Pausado':
            print(f"  ⚠️ Envio pausado. Movendo para Processados e ignorando.")
            mover_arquivo_drive(drive_service, drive_id, config.id_pasta_processados)
            registrar_log(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_logs, config.nome_aba_clientes,
                dados_cliente['identificador'], dados_cliente['nome'],
                "IGNORADO", "Envio Pausado"
            )
            continue

        # 5b. Download do PDF
        print(f"  [*] Baixando PDF do Drive...")
        caminho_local = descarregar_relatorio(drive_service, drive_id, nome_arquivo)
        print(f"  ✅ PDF baixado: {caminho_local} ({os.path.getsize(caminho_local)} bytes)")

        # 6. Validação
        print(f"  [*] Validando relatório...")
        validacao = validar_relatorio(caminho_local)
        if not validacao.get("valido", True):
            print(f"  ⚠️ Relatório INVÁLIDO: {validacao['justificativa']}")
            mover_arquivo_drive(drive_service, drive_id, config.id_pasta_processados)
            registrar_log(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_logs, config.nome_aba_clientes,
                dados_cliente['identificador'], dados_cliente['nome'],
                "PULADO", validacao['justificativa']
            )
            os.remove(caminho_local)
            continue
        print(f"  ✅ Relatório válido: {validacao['justificativa']}")

        # 7. Gerar mensagem
        print(f"  [*] Gerando mensagem...")
        msg_whatsapp, resumo_log = gerar_mensagem_fallback(dados_cliente)
        print(f"  ✅ Mensagem ({len(msg_whatsapp)} chars):")
        for linha in msg_whatsapp.split('\n')[:3]:
            print(f"     {linha}")

        # 8. Enviar via Baileys
        print(f"  [*] Enviando PDF + mensagem via Baileys...")
        sucesso = client.send_pdf_and_text(
            dados_cliente['telefone'],
            caminho_local,
            nome_arquivo,
            msg_whatsapp,
        )

        # 9. Pós-processamento
        if sucesso:
            processados += 1
            print(f"  ✅ ENVIO REALIZADO! ({processados}/{limite})")
            mover_arquivo_drive(drive_service, drive_id, config.id_pasta_processados)
            print(f"  ✅ PDF movido para Processados")
            registrar_log(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_logs, config.nome_aba_clientes,
                dados_cliente['identificador'], dados_cliente['nome'],
                "SUCESSO", msg_whatsapp
            )
            print(f"  ✅ Log registrado na planilha")
            atualizar_ultimo_resumo(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_clientes,
                dados_cliente['numero_linha'], msg_whatsapp
            )
            marcar_status_envio(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_clientes,
                dados_cliente['numero_linha'], True
            )
        else:
            print(f"  ❌ FALHA no envio")
            registrar_log(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_logs, config.nome_aba_clientes,
                dados_cliente['identificador'], dados_cliente['nome'],
                "FALHA_ENVIO", "Erro no Baileys"
            )
            marcar_status_envio(
                sheets_service, config.id_planilha_clientes,
                config.nome_aba_clientes,
                dados_cliente['numero_linha'], False
            )

        # Limpeza
        if os.path.exists(caminho_local):
            os.remove(caminho_local)

    # ═══ PASSO 10: Encerrar Baileys ═══
    print(f"\n{'─'*40}")
    print("PASSO 10: Encerrando Baileys")
    manager.encerrar()

    # ═══ RESULTADO ═══
    print(f"\n{'='*60}")
    print(f"  ✅ PIPELINE CONCLUÍDA")
    print(f"  Envios realizados: {processados}/{limite}")
    print(f"  Verifique a planilha: https://docs.google.com/spreadsheets/d/{config.id_planilha_clientes}")
    print(f"  Verifique os PDFs processados na pasta Processados do Drive")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
