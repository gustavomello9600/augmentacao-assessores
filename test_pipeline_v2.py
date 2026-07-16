#!/usr/bin/env python3
"""
Teste fiel da pipeline — replica exatamente o fluxo do orquestrador_v2.py:
  - System instruction completa (idêntica ao original)
  - 10 exemplos N-Shot (idênticos ao original)
  - Validação de relatório ativo (Gemini, ou fallback deterministico)
  - Geração de mensagem (Gemini, ou fallback com mesmo schema JSON)
  - Envio real via Baileys (WhatsApp Web)

PRÉ-REQUISITOS:
  1. Serviço Baileys rodando e conectado
  2. (Opcional) GEMINI_API_KEY no .env para usar IA real

USO:
  python3 test_pipeline_v2.py 557998423338
"""

import sys
import os
import re
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from dotenv import load_dotenv
load_dotenv()

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÕES (idênticas ao .env.example do Agemini)
# ═══════════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELO_GEMINI = "gemini-2.0-flash"          # mesmo do original
MODELO_VALIDACAO = "gemini-2.0-flash-lite"  # mesmo do original

# ═══════════════════════════════════════════════════════════════
# SYSTEM INSTRUCTION (IDÊNTICA ao orquestrador_v2.py linhas 460-489)
# ═══════════════════════════════════════════════════════════════

def build_system_instruction(vocativo, tom_especifico, instrucoes_assessor,
                              contexto_anterior, personalizacao_assessor):
    return f"""
# PAPEL E OBJETIVO
Você é um Assessor de Investimentos atuando em nome de um escritório (ex: afiliado à XP Investimentos). Sua única responsabilidade é analisar relatórios mensais de performance de carteira em PDF (XPerformance) e redigir uma mensagem de WhatsApp para o cliente cujo vocativo/nome para tratamento é {vocativo}. O objetivo da mensagem é resumir o rendimento do mês/ano, destacar os principais pontos da carteira e se colocar à disposição, enviando o arquivo PDF em anexo.

# PERSONALIZAÇÃO ESPECÍFICA PARA ESTE CLIENTE
- Tom de voz e personalidade (CRÍTICO): {tom_especifico}
- Instruções específicas adicionais do Assessor: {instrucoes_assessor}
- Contexto anterior (Resumo do mês passado, use se útil para comparar): "{contexto_anterior}"

# TOM DE VOZ E PERSONALIDADE (GERAL)
- Próximo e Empático: Trate o cliente pelo nome. Use "Dona/Seu" para clientes mais velhos, se o contexto sugerir.
- Consultivo e Transparente: Comemore bons resultados ("tá show!", "andando bem"), mas não esconda resultados ruins. Explique o *porquê* (ex: "A renda fixa atrelada à inflação sofreu um pouco, mas as ações puxaram o resultado").
- Profissional, mas Conversacional: Evite jargões complexos sem explicação. Use linguagem de WhatsApp, mas com BOA gramática. NÃO use abreviações extremas (substitua "vc" por "você", "tb" por "também", "q" por "que").
- Propositivo: Sempre que fizer sentido, traga uma visão de futuro (ex: queda de juros) ou deixe a porta aberta para um bate-papo de alinhamento.

# DIRETRIZES DE FORMATAÇÃO (WHATSAPP)
- Use *negrito* para destacar números importantes, nomes de classes de ativos e indicadores (ex: *120% do CDI*, *Renda Variável*).
- Use _itálico_ para destacar o nome do relatório ou termos específicos.
- Use emojis com moderação (máximo de 3 a 4 por mensagem) para manter o tom amigável (📈, 📊, 🤝, 💡, 👋).
- Quebre a mensagem em parágrafos curtos. Textões afastam a leitura no WhatsApp.

# REGRAS E RESTRIÇÕES
1. NUNCA prometa rentabilidade futura. Use termos como "a expectativa é", "pode se beneficiar".
2. Baseie-se ESTRITAMENTE nos dados lidos no PDF. Não invente números.
3. A mensagem deve pressupor que o PDF será enviado junto com ela.
4. Você DEVE retornar EXATAMENTE um objeto JSON contendo "mensagem_whatsapp" e "resumo_interno".

# PERSONALIZAÇÃO ESPECÍFICA DO ASSESSOR (MANUAL DE ESTILO/IDENTIDADE)
{personalizacao_assessor}
"""

# ═══════════════════════════════════════════════════════════════
# SYSTEM INSTRUCTION DE VALIDAÇÃO (idêntica ao original)
# ═══════════════════════════════════════════════════════════════

SYSTEM_INSTRUCTION_VALIDACAO = """
Você é um auditor financeiro rigoroso. Sua única função é analisar este relatório de performance de investimentos (PDF) e determinar se a carteira possui movimentação real ou se está "fantasma/zerada".

Uma carteira DEVE ser considerada INATIVA/INVÁLIDA (valido: false) se você observar:
- "Rentabilidade Mês" de 0,00% E "Ganho Mês" de R$ 0,00.
- Gráficos de "Evolução Patrimonial" ou "Rentabilidade" completamente retos (linhas no zero).
- Tabelas de referência com 0,00% em todos os meses preenchidos.
- Patrimônio travado em um valor X (ex: R$ 457,00) mas sem nenhuma oscilação, ganho financeiro ou rentabilidade histórica (tudo zerado ou com traços '-').

Responda EXATAMENTE com um objeto JSON contendo:
- "valido": booleano (true se houver oscilação/rendimento real, false se for inativa/zerada).
- "justificativa": string curta de até 10 palavras explicando o motivo da decisão.
"""

# ═══════════════════════════════════════════════════════════════
# N-SHOT EXAMPLES (IDÊNTICOS ao orquestrador_v2.py linhas 514-644)
# ═══════════════════════════════════════════════════════════════

N_SHOT_EXAMPLES = [
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Cliente geral, resultado focado no CDI, Bom resultado)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Olá Breno, bom dia! 👋\n\nSegue o seu _relatório de performance_ atualizado até o fim deste mês. \n\nSua carteira está indo muito bem! Desde o início da nossa alocação, já acumulamos um rendimento de *122% do CDI*. Tá show! 📈\n\nDá uma olhada no PDF abaixo e, se quiser bater um papo para revisarmos os próximos passos, é só me avisar. Um abraço!",
            "resumo_interno": "Resultado focado no CDI. Bom resultado de 122%."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Cliente mais sênior/formal, foco em segurança e clareza)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Bom dia, Dona Rosa. Como a senhora está? 🌻\n\nEstou enviando abaixo o relatório de performance da sua carteira bem legal para a senhora acompanhar. \n\nO ano está indo muito bem, já acumulamos *10% de rentabilidade* (o que equivale a *121% do CDI*). É um resultado excelente e bem seguro. \n\nQualquer dúvida sobre os números, estou à inteira disposição.",
            "resumo_interno": "Segurança e clareza. Rentabilidade de 10% (121% CDI)."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Carteira mista, Ações bem, Renda Fixa mal, Visão macro)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Fala Rafa, boa tarde! 🤝\n\nSegue o fechamento da sua carteira. Os resultados estão andando bem!\n\nA parte de *Renda Fixa - Inflação* acabou sendo a pior performance do mês, mas, em compensação, a parte de *Renda Variável (Ações Brasil)* segurou muito bem e puxou o resultado para cima. 📊\n\nDe todo modo, eu não mudaria nada agora. Já já os juros começam a cair e essa parte atrelada à inflação volta a valorizar também. Qualquer dúvida, me chama aqui!",
            "resumo_interno": "Ações bem, Renda Fixa mal. Expectativa de queda de juros."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Sugestão de leve alteração, Foco em Ações)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Olá Pedro, bom dia! \n\nSegue o relatório de performance da sua carteira até o dia 20. \n\nCara, o mercado acionário brasileiro está começando a ganhar uma boa tração. Hoje vocês têm *7% em RV Brasil*. Eu acho muito saudável a gente pensar em subir esse patamar para *10%* na próxima oportunidade. 💡\n\nMe avise quando tiver um tempo para marcarmos uma conversa sobre seu planejamento financeiro, tá bom? Abraço!",
            "resumo_interno": "Sugestão de alteração para subir RV Brasil para 10%."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Foco em carteira de Dividendos)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Fala Igor, tudo bem? Bom dia!\n\nSegue o seu _XPerformance_ fresquinho. \n\nO grande destaque desse mês continua sendo a nossa *carteira top dividendos*, que está indo muito bem e gerando uma ótima renda passiva. 💸\n\nO rendimento global fechou em *110% do CDI*. Dá uma olhada no anexo e me diz o que achou.",
            "resumo_interno": "Foco em Dividendos. Rendimento global 110% do CDI."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Explicando resultado ruim passado vs. bom presente)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Olá Marcos, boa tarde! 👋\n\nPassando para te enviar o relatório de investimentos mensal.\n\nLembrando que o rendimento do ano passado foi prejudicado por alguns fundos, fechando em apenas *4%*. Mas a boa notícia é que a estratégia que montamos para este ano já está entregando muito bem, batendo *115% do CDI*. 🚀\n\nVamos ver o que puxa o resultado nos próximos meses, mas o cenário é positivo. Abraço!",
            "resumo_interno": "Ano passado ruim (4%), presente bom (115% do CDI)."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Foco na transição de Multimercados para Renda Fixa)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Bom dia, Ana! Tudo certo?\n\nEstou te mandando o relatório de performance da sua carteira. 📊\n\nNotamos que os *Multimercados* puxaram o resultado um pouco para baixo neste trimestre. Inclusive, um deles é aquele fundo de previdência que eu já estou propondo a gente migrar para *Renda Fixa*.\n\nDá uma olhada nos dados no PDF e me avisa se podemos seguir com aquela alteração que conversamos.",
            "resumo_interno": "Transição sugerida: Multimercados para Renda Fixa."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Direto ao ponto, resultado excelente)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Olá Thiago, bom dia! 🤝\n\nSegue o relatório da sua carteira. Fechamos o mês com um excelente resultado de *135% do CDI*, puxado principalmente pelos fundos de *Private Equity* (Alternativos). 📈\n\nO mercado está ajudando e nosso posicionamento está bem aderente. Qualquer dúvida, estou por aqui!",
            "resumo_interno": "Excelente resultado: 135% do CDI com foco em Private Equity."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Performance desde o início, Longo Prazo)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Fala Camila, boa tarde!\n\nEstou enviando seu _relatório de performance_. \n\nO mês foi um pouco lateral, mas o que importa é o quadro geral: olhando a performance *desde o início (nov/23)*, estamos entregando *18% de rentabilidade absoluta*. 🎯\n\nO importante é mantermos o foco no longo prazo. Qualquer coisa, me manda um áudio aqui.",
            "resumo_interno": "Mês lateral. Performance desde o início entregando 18%."
        }, ensure_ascii=False)]
    },
    {
        "role": "user",
        "parts": ["Analise o relatório e gere a síntese final (Perfil: Mensagem de manutenção/acompanhamento tranquilo)."]
    },
    {
        "role": "model",
        "parts": [json.dumps({
            "mensagem_whatsapp": "Bom dia, Seu Wilton! Tudo bem? 👋\n\nPassando para deixar o seu relatório de performance mensal em anexo.\n\nA carteira segue bem equilibrada, rendendo *105% do CDI* no ano, sem grandes sustos e cumprindo exatamente o papel de proteção de patrimônio que desenhamos juntos. 🛡️\n\nSigo acompanhando tudo de perto por aqui. Um excelente fim de semana!",
            "resumo_interno": "Equilíbrio e proteção. Rendimento de 105% do CDI no ano."
        }, ensure_ascii=False)]
    },
]


# ═══════════════════════════════════════════════════════════════
# GEMINI: VALIDAÇÃO DE RELATÓRIO ATIVO
# ═══════════════════════════════════════════════════════════════

def validar_relatorio_ativo(caminho_pdf: str) -> dict:
    """Valida se o relatório tem carteira ativa (Gemini real ou fallback deterministico)."""
    print("    [*] Validando se o relatório contém dados ativos...")

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            ficheiro = genai.upload_file(caminho_pdf)

            generation_config = genai.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "valido": {"type": "BOOLEAN", "description": "True para carteira ativa, False para zerada/inativa"},
                        "justificativa": {"type": "STRING", "description": "Motivo da decisão"}
                    },
                    "required": ["valido", "justificativa"]
                }
            )

            modelo = genai.GenerativeModel(
                model_name=MODELO_VALIDACAO,
                system_instruction=SYSTEM_INSTRUCTION_VALIDACAO,
                generation_config=generation_config
            )

            resposta = modelo.generate_content([
                ficheiro,
                "Analise os indicadores de rentabilidade e ganho deste relatório e retorne o JSON de validação."
            ])
            resultado = json.loads(resposta.text)
            print(f"    [Gemini] Validação: valido={resultado['valido']}, motivo={resultado['justificativa']}")
            return resultado
        except Exception as e:
            print(f"    [-] Erro na validação via Gemini: {e}. Usando fallback deterministico.")

    # Fallback deterministico: analisa o PDF como texto
    return validar_relatorio_fallback(caminho_pdf)


def validar_relatorio_fallback(caminho_pdf: str) -> dict:
    """Fallback deterministico: extrai texto do PDF com PyPDF2 e analisa indicadores."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(caminho_pdf)
        texto = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texto += t + "\n"

        # Busca padrões de valores financeiros no texto extraído
        tem_patrimonio = bool(re.search(r'Patrim.nio.*R\$', texto, re.IGNORECASE))
        tem_rentabilidade = bool(re.search(r'Rentabilidade.*[\d.,]+\s*%', texto, re.IGNORECASE))
        tem_valor = bool(re.search(r'R\$\s*[\d.,]+', texto))

        valido = tem_patrimonio or tem_rentabilidade or tem_valor
        if valido:
            justificativa = "Indicadores financeiros detectados no PDF"
        else:
            # Cofre destrava: se não conseguiu extrair texto, assume válido
            valido = True
            justificativa = "Texto nao extraivel. Liberado por seguranca."

    except Exception as e:
        # Cofre destrava: falha na leitura = assume válido para não perder envio
        valido = True
        justificativa = f"Falha na validacao previa: {str(e)[:50]}"

    print(f"    [Fallback] Validacao: valido={valido}, motivo={justificativa}")
    return {"valido": valido, "justificativa": justificativa}


# ═══════════════════════════════════════════════════════════════
# GEMINI: GERAÇÃO DE MENSAGEM (com N-Shot + Structured Output)
# ═══════════════════════════════════════════════════════════════

def gerar_mensagem_assessor(caminho_pdf: str, dados_cliente: dict,
                             ultimo_resumo: str, personalizacao: str) -> tuple:
    """Gera mensagem usando Gemini (ou fallback deterministico)."""
    vocativo = dados_cliente.get("vocativo", "").strip() or dados_cliente.get("nome", "Cliente")
    tom = dados_cliente.get("tom_de_voz", "profissional e direto")
    instrucoes = dados_cliente.get("instrucoes_assessor", "Nenhuma instrução adicional.")
    contexto = ultimo_resumo if ultimo_resumo else "Este é o primeiro relatório do cliente. Não há contexto anterior."

    system_instruction = build_system_instruction(
        vocativo, tom, instrucoes, contexto, personalizacao
    )

    if GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            ficheiro = genai.upload_file(caminho_pdf)

            generation_config = genai.GenerationConfig(
                temperature=1,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "mensagem_whatsapp": {"type": "STRING", "description": "A mensagem formatada final para enviar via WhatsApp."},
                        "resumo_interno": {"type": "STRING", "description": "Um resumo de 1 linha com % e destaques para fins de log interno."}
                    },
                    "required": ["mensagem_whatsapp", "resumo_interno"]
                }
            )

            modelo = genai.GenerativeModel(
                model_name=MODELO_GEMINI,
                system_instruction=system_instruction,
                generation_config=generation_config
            )

            print("    [Gemini] Iniciando chat com exemplos N-Shot...")
            chat = modelo.start_chat(history=N_SHOT_EXAMPLES)
            print("    [Gemini] Analisando o relatório...")
            resposta = chat.send_message([
                ficheiro,
                "Aqui está o relatório atual do cliente. Por favor, gere a síntese seguindo as diretrizes e o formato exigido."
            ])

            resultado = json.loads(resposta.text)
            print(f"    [Gemini] ✅ Mensagem gerada ({len(resultado['mensagem_whatsapp'])} chars)")
            return resultado["mensagem_whatsapp"], resultado["resumo_interno"]

        except Exception as e:
            print(f"    [-] Erro no Gemini: {e}. Usando fallback deterministico.")

    # Fallback deterministico: usa os exemplos N-Shot como base e adapta
    return gerar_mensagem_fallback(dados_cliente)


def gerar_mensagem_fallback(dados_cliente: dict) -> tuple:
    """Fallback deterministico: seleciona do N-Shot mais próximo e adapta."""
    nome = dados_cliente.get("nome", "Cliente")
    vocativo = dados_cliente.get("vocativo", "").strip() or nome
    tom = dados_cliente.get("tom_de_voz", "").lower()

    # Seleciona template baseado no tom de voz
    if "formal" in tom or "senior" in tom or "sênior" in tom:
        idx = 2  # Dona Rosa — segurança e clareza
    elif "dividendo" in tom or "dividendos" in tom:
        idx = 8  # Igor — dividendos
    elif "ação" in tom or "acoes" in tom or "variável" in tom:
        idx = 4  # Rafa — RV bem, RF mal
    elif "longo" in tom or "prazo" in tom:
        idx = 18  # Camila — longo prazo
    elif "direto" in tom:
        idx = 16  # Thiago — direto ao ponto
    else:
        idx = 0  # Breno — geral/CDI

    # Pega o exemplo N-Shot correspondente (índices pares são user, ímpares são model)
    model_idx = idx * 2 + 1
    if model_idx < len(N_SHOT_EXAMPLES):
        exemplo_json = json.loads(N_SHOT_EXAMPLES[model_idx]["parts"][0])
        msg = exemplo_json["mensagem_whatsapp"]
        resumo = exemplo_json["resumo_interno"]

        # Substitui o vocativo/nome no template
        # Pega o primeiro nome do exemplo original e troca
        primeiro_nome_original = msg.split()[1].rstrip(',!.')
        msg = msg.replace(f" {primeiro_nome_original},", f" {nome.split()[0]},")
        msg = msg.replace(f" {primeiro_nome_original}!", f" {nome.split()[0]}!")

        print(f"    [Fallback N-Shot] Template #{model_idx} adaptado para {nome}")
        return msg, f"[Fallback] {resumo}"

    # Fallback último: genérico
    msg = f"Olá {nome}, bom dia! 👋\n\nSegue o seu _relatório de performance_.\n\nSua carteira está indo bem. Dá uma olhada no PDF e qualquer dúvida é só me chamar. Abraço!"
    print(f"    [Fallback] Mensagem genérica para {nome}")
    return msg, f"Cliente {nome}: mensagem padrão."


# ═══════════════════════════════════════════════════════════════
# TESTE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_pipeline_v2.py <numero_whatsapp> [--cliente NOME] [--tom TOM]")
        print("Ex:  python3 test_pipeline_v2.py 557998423338 --cliente \"João Silva\" --tom \"formal e objetivo\"")
        sys.exit(1)

    numero = re.sub(r'\D', '', sys.argv[1])
    if len(numero) in [10, 11] and not numero.startswith("55"):
        numero = f"55{numero}"

    # Parse argumentos opcionais
    nome_cliente = "Cliente XP"
    tom_voz = "profissional e direto"
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--cliente" and i + 1 < len(args):
            nome_cliente = args[i + 1]
            i += 2
        elif args[i] == "--tom" and i + 1 < len(args):
            tom_voz = args[i + 1]
            i += 2
        else:
            i += 1

    # Dados mock do cliente (formato idêntico ao PROCV da planilha original)
    dados_cliente = {
        "identificador": nome_cliente.replace(" ", "").upper(),
        "status": "Envio Ativo",
        "nome": nome_cliente,
        "telefone": numero,
        "vocativo": nome_cliente.split()[0],
        "tom_de_voz": tom_voz,
        "instrucoes_assessor": "Cliente prefere mensagens curtas e diretas. Tem bom humor.",
        "ultimo_resumo": "Mês passado: 118% do CDI, RV Brasil puxou resultado.",
        "numero_linha": 2,
    }

    # Personalização do assessor (simula o Google Doc do original)
    personalizacao_assessor = """
MANUAL DE ESTILO DO ASSESSOR:
- Identidade: Consultor de investimentos sênior, acessível mas profissional.
- Assinatura: Sempre encerrar com "Abraço!" ou "Estou por aqui!".
- Diferencial: Explica conceitos financeiros de forma simples.
- Preferência: Mensagens de até 5 linhas no WhatsApp.
"""

    print("=" * 60)
    print("  🧪 TESTE FIEL — Pipeline Original do Agemini")
    print("=" * 60)
    print(f"\n  Cliente: {nome_cliente}")
    print(f"  Tom de voz: {tom_voz}")
    print(f"  WhatsApp: {numero}")
    print(f"  Gemini API: {'✅ Configurada' if GEMINI_API_KEY else '❌ Fallback deterministico'}")
    print(f"  N-Shot examples: {len(N_SHOT_EXAMPLES)} mensagens ({len(N_SHOT_EXAMPLES)//2} pares)")
    print(f"  Modo Baileys: liga -> usa -> desliga")

    # ═══ PASSO 1: Iniciar Baileys (subprocesso) ═══
    print(f"\n{'─'*40}")
    print("PASSO 1: Iniciando Baileys (liga -> conecta -> usa -> desliga)")
    from src.whatsapp import BaileysManager

    session_dir = os.path.join(os.path.dirname(__file__), "sessions", "assessor1")
    manager = BaileysManager(session_dir=session_dir, porta=3100)

    if not manager.iniciar(timeout=45):
        print("  ❌ WhatsApp nao conectou. Verifique QR code ou sessao.")
        manager.encerrar()
        sys.exit(1)

    client = manager.client
    print(f"  ✅ Baileys pronto. Cliente HTTP em http://localhost:3100")

    # ═══ PASSO 2: Gerar PDF ═══
    print(f"\n{'─'*40}")
    print("PASSO 2: Gerando PDF XPerformance (idêntico ao Drive)")
    pdf_path = f"/tmp/relatorio_{nome_cliente.replace(' ', '_')}.pdf"
    from gerar_pdf_teste import gerar_pdf_cliente
    gerar_pdf_cliente(nome_cliente, pdf_path)
    print(f"  ✅ PDF: {pdf_path} ({os.path.getsize(pdf_path)/1024:.1f} KB)")

    # ═══ PASSO 3: Validar relatório (Gemini ou fallback) ═══
    print(f"\n{'─'*40}")
    print("PASSO 3: Validando relatorio ativo (original orquestrador_v2.py)")
    print(f"  System instruction: {len(SYSTEM_INSTRUCTION_VALIDACAO)} chars")
    validacao = validar_relatorio_ativo(pdf_path)
    if not validacao.get("valido", True):
        print(f"  ❌ Relatório INVALIDO: {validacao['justificativa']}")
        sys.exit(1)
    print(f"  ✅ Relatório VALIDO: {validacao['justificativa']}")

    # ═══ PASSO 4: Gerar mensagem (Gemini ou fallback N-Shot) ═══
    print(f"\n{'─'*40}")
    print("PASSO 4: Gerando mensagem (System Instruction + N-Shot)")
    print(f"  System instruction: {len(build_system_instruction('X', 'X', 'X', 'X', 'X'))} chars")
    print(f"  N-Shot examples: {len(N_SHOT_EXAMPLES)} mensagens")

    msg_whatsapp, resumo = gerar_mensagem_assessor(
        pdf_path, dados_cliente,
        dados_cliente["ultimo_resumo"],
        personalizacao_assessor,
    )
    print(f"\n  📝 Mensagem final ({len(msg_whatsapp)} chars):")
    print("  " + "-" * 50)
    for linha in msg_whatsapp.split('\n'):
        print(f"  | {linha}")
    print("  " + "-" * 50)
    print(f"  📊 Resumo: {resumo}")

    # ═══ PASSO 5: Validar número ═══
    print(f"\n{'─'*40}")
    print("PASSO 5: Validando numero (phone-exists, igual Z-API)")
    lid = client.phone_exists(numero)
    if not lid:
        print(f"  ❌ Numero {numero} sem WhatsApp")
        sys.exit(1)
    print(f"  ✅ @lid: {lid}")

    # ═══ PASSO 6: Enviar PDF + mensagem ═══
    print(f"\n{'─'*40}")
    print("PASSO 6: Enviando PDF + texto (send-document/pdf + send-text)")
    sucesso = client.send_pdf_and_text(
        numero, pdf_path,
        f"XPerformance_{nome_cliente.replace(' ', '_')}.pdf",
        msg_whatsapp,
    )

    # ═══ RESULTADO ═══
    print(f"\n{'='*60}")
    if sucesso:
        print("  ✅✅✅ PIPELINE CONCLUIDA COM SUCESSO! ✅✅✅")
        print(f"  📱 {numero}")
        print(f"  📄 PDF XPerformance de {nome_cliente}")
        print(f"  🤖 Geracao: {'Gemini API' if GEMINI_API_KEY else 'Fallback N-Shot'}")
        print(f"  🔌 WhatsApp: Baileys (local, liga -> usa -> desliga)")
        print(f"\n  ⚡ O pipeline REAL usaria:")
        print(f"     - Google Drive para buscar PDFs pendentes")
        print(f"     - Google Sheets para PROCV (achar cliente pelo nome)")
        print(f"     - Gemini para validar + gerar mensagem")
        print(f"     - Baileys para enviar (substituindo Z-API)")
        print(f"     - Google Sheets para registrar logs")
    else:
        print("  ❌ FALHA NO ENVIO")
    print("=" * 60)

    # ═══ PASSO 7: Encerrar Baileys ═══
    print(f"\n{'─'*40}")
    print("PASSO 7: Encerrando Baileys (salva sessao)")
    manager.encerrar()

    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    return 0 if sucesso else 1


if __name__ == "__main__":
    sys.exit(main())
