#!/usr/bin/env python3
"""
Teste completo da pipeline de Aumentacao de Assessores.
Mocka Google Drive/Sheets/Gemini e testa envio real via Baileys.

PREREQUISITOS:
  1. Servico Baileys rodando (node baileys_service.js)
  2. WhatsApp conectado (QR code escaneado)
  3. Numero de WhatsApp para receber o teste

USO:
  python3 test_pipeline.py <seu_numero_whatsapp>
  Ex: python3 test_pipeline.py 5511999999999
"""

import sys
import os
import json
import random
from pathlib import Path

# Adiciona src/ ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.whatsapp import BaileysClient
from src.config import AssessorConfig


# ═══════════════════════════════════════════════════════════════
# GERADOR DE PDF FICCIONAL
# ═══════════════════════════════════════════════════════════════

def gerar_pdf_rapido(nome_cliente: str, output_path: str) -> str:
    """Wrapper para o gerador de PDF."""
    from gerar_pdf_teste import gerar_pdf_cliente
    return gerar_pdf_cliente(nome_cliente, output_path)


# ═══════════════════════════════════════════════════════════════
# MENSAGEM FICCIONAL (mock do Gemini)
# ═══════════════════════════════════════════════════════════════

def gerar_mensagem_mock(nome_cliente: str) -> tuple[str, str]:
    """Simula a geracao de mensagem pelo Gemini (sem chamar API)."""
    templates = [
        (
            f"Ola {nome_cliente}, bom dia! 👋\n\n"
            f"Segue o seu *relatorio de performance* atualizado. "
            f"Sua carteira esta indo bem, com rendimento acima do CDI nos ultimos meses. 📈\n\n"
            f"De uma olhada no PDF em anexo e, se quiser bater um papo sobre alocacao, "
            f"e so me chamar. Abraco!",
            f"Cliente {nome_cliente}: rendimento acima do CDI, sem alteracoes sugeridas."
        ),
        (
            f"Fala {nome_cliente}, boa tarde! 🤝\n\n"
            f"Segue o fechamento da sua carteira. A *Renda Variavel* puxou bem o resultado "
            f"esse mes, compensando a Renda Fixa que ficou lateral. 📊\n\n"
            f"No cenario atual, manteria as alocacoes. Qualquer duvida, me manda um audio!",
            f"Cliente {nome_cliente}: RV bem, RF lateral. Manter alocacao."
        ),
        (
            f"Ola {nome_cliente}, tudo bem?\n\n"
            f"Estou enviando seu _XPerformance_ do mes. O destaque fica por conta "
            f"da *carteira de dividendos*, gerando otima renda passiva. 💸\n\n"
            f"O rendimento global fechou em *115% do CDI*. De uma olhada no PDF!",
            f"Cliente {nome_cliente}: foco dividendos, 115% CDI."
        ),
    ]
    msg, resumo = random.choice(templates)
    return msg, resumo


# ═══════════════════════════════════════════════════════════════
# TESTE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_pipeline.py <seu_numero_whatsapp>")
        print("Ex:   python3 test_pipeline.py 5511999999999")
        sys.exit(1)

    numero_teste = sys.argv[1]
    # Limpa caracteres nao numericos
    import re
    numero_teste = re.sub(r'\D', '', numero_teste)

    # Adiciona DDI 55 se for numero brasileiro sem DDI
    if len(numero_teste) in [10, 11] and not numero_teste.startswith("55"):
        numero_teste = f"55{numero_teste}"

    print("=" * 60)
    print("  🧪 TESTE DA PIPELINE DE AUMENTACAO DE ASSESSORES")
    print("=" * 60)
    print(f"\n  Numero de teste: {numero_teste}")
    print(f"  Servico Baileys: http://localhost:3100")

    # ═══ PASSO 1: Verificar servico Baileys ═══
    print("\n--- PASSO 1: Verificando servico Baileys ---")
    client = BaileysClient(base_url="http://localhost:3100")

    try:
        import requests
        health = requests.get("http://localhost:3100/health", timeout=5).json()
        print(f"  Status: {health['status']}")

        if health['status'] != 'connected':
            print("\n  ❌ WhatsApp NAO conectado!")
            if health.get('has_qr'):
                print("  📱 QR Code disponivel. Escaneie antes de continuar:")
                qr_resp = requests.get("http://localhost:3100/qr", timeout=5).json()
                if 'qr' in qr_resp:
                    import base64
                    b64 = qr_resp['qr'].split(',', 1)[-1] if ',' in qr_resp['qr'] else qr_resp['qr']
                    img = base64.b64decode(b64)
                    qr_path = '/opt/data/augmentacao-assessores/qr_code.png'
                    with open(qr_path, 'wb') as f:
                        f.write(img)
                    print(f"  📷 QR Code salvo em: {qr_path}")
                    print("  Abra o arquivo e escaneie com o WhatsApp.")
            print("\n  Execute novamente apos conectar o WhatsApp.")
            sys.exit(1)

        print("  ✅ WhatsApp conectado! Prosseguindo...")
    except Exception as e:
        print(f"\n  ❌ Servico Baileys nao respondeu: {e}")
        print("  Certifique-se de que 'node baileys_service.js' esta rodando.")
        sys.exit(1)

    # ═══ PASSO 2: Gerar PDF de teste ═══
    print("\n--- PASSO 2: Gerando PDF de relatorio XPerformance ---")
    nome_cliente = "Cliente Teste"
    pdf_path = f"/tmp/relatorio_teste_pipeline.pdf"
    gerar_pdf_rapido(nome_cliente, pdf_path)
    tamanho_kb = os.path.getsize(pdf_path) / 1024
    print(f"  ✅ PDF gerado: {pdf_path} ({tamanho_kb:.1f} KB)")

    # ═══ PASSO 3: Gerar mensagem (mock Gemini) ═══
    print("\n--- PASSO 3: Gerando mensagem personalizada ---")
    msg_whatsapp, resumo = gerar_mensagem_mock(nome_cliente)
    print(f"  📝 Mensagem gerada:")
    for linha in msg_whatsapp.split('\n'):
        print(f"     {linha}")
    print(f"  📊 Resumo interno: {resumo}")

    # ═══ PASSO 4: Verificar numero no WhatsApp ═══
    print(f"\n--- PASSO 4: Verificando numero {numero_teste} ---")
    lid = client.phone_exists(numero_teste)
    if not lid:
        print(f"  ❌ Numero {numero_teste} nao encontrado no WhatsApp.")
        print("  Verifique se o numero esta correto e tem WhatsApp.")
        sys.exit(1)
    print(f"  ✅ Numero validado! @lid: {lid}")

    # ═══ PASSO 5: Enviar PDF + Mensagem ═══
    print(f"\n--- PASSO 5: Enviando PDF + mensagem ---")
    sucesso = client.send_pdf_and_text(
        numero_teste,
        pdf_path,
        "XPerformance_Cliente_Teste.pdf",
        msg_whatsapp,
    )

    # ═══ RESULTADO ═══
    print("\n" + "=" * 60)
    if sucesso:
        print("  ✅✅✅ TESTE CONCLUIDO COM SUCESSO! ✅✅✅")
        print(f"  📱 PDF + mensagem enviados para {numero_teste}")
        print(f"  📄 Relatorio: XPerformance_Cliente_Teste.pdf")
        print(f"  💬 Mensagem: {resumo}")
    else:
        print("  ❌ FALHA NO ENVIO")
        print("  Verifique os logs do servico Baileys para mais detalhes.")
    print("=" * 60)

    # Limpeza
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    return 0 if sucesso else 1


if __name__ == "__main__":
    sys.exit(main())
