#!/usr/bin/env python3
"""
Monta a estrutura completa de teste no Google Drive usando OAuth pessoal (GAPI).

Cria:
  1. Pasta raiz: "Augmentacao-Assessores-Teste"
     ├── Pendentes/          (onde os PDFs chegam)
     └── Processados/        (para onde vao apos envio)
  2. Planilha Google Sheets com abas:
     - Clientes (A:ID, B:Status, C:Nome, D:Telefone, E:Vocativo, F:Tom, G:Instrucoes, H:StatusEnvio, I:UltimoResumo)
     - Registros (A:Data/Hora, B:ID_Relatorio, C:Nome_Cliente, D:Status, E:Detalhes)
  3. Google Docs "Personalizacao-Assessor-Teste"
  4. PDFs de relatorio na pasta Pendentes
  5. Compartilha tudo com a service account (editor)

Uso:
  python3 setup_drive_teste.py
"""

import subprocess
import json
import os
import sys
import time
from pathlib import Path

# ── Config ─────────────────────────────────────────
GAPI = "/opt/data/venvs/google/bin/python /opt/data/skills/productivity/google-workspace/scripts/google_api.py"
SERVICE_ACCOUNT_EMAIL = "servi-o-drive-id@idata-421319.iam.gserviceaccount.com"
ROOT_NAME = "Augmentacao-Assessores-Teste"

# IDs preenchidos durante a execucao
ROOT_ID = None
PENDENTES_ID = None
PROCESSADOS_ID = None
PLANILHA_ID = None
DOC_PERSONALIZACAO_ID = None


def gapi(*args):
    """Executa GAPI e retorna JSON parseado."""
    cmd = GAPI.split() + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  ❌ GAPI erro: {result.stderr[:300]}")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  ⚠️ JSON invalido: {result.stdout[:200]}")
        return None


def share_with_sa(file_id: str, role: str = "writer"):
    """Compartilha arquivo/pasta com a service account."""
    print(f"  [share] Compartilhando {file_id} com {SERVICE_ACCOUNT_EMAIL}...")
    result = subprocess.run(
        GAPI.split() + ["drive", "share", file_id, "--email", SERVICE_ACCOUNT_EMAIL, "--role", role],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        print(f"    ✅ Compartilhado como {role}")
    else:
        print(f"    ⚠️ Share falhou: {result.stderr[:200]}")


# ═══════════════════════════════════════════════════
# PASSO 1: Criar pasta raiz + subpastas
# ═══════════════════════════════════════════════════
print("═══ PASSO 1: Criando pastas no Drive ═══")

# Raiz
result = gapi("drive", "create-folder", ROOT_NAME)
if not result:
    print("❌ Falha ao criar pasta raiz")
    sys.exit(1)
ROOT_ID = result["id"]
print(f"  ✅ Raiz: {ROOT_NAME} → {ROOT_ID}")
share_with_sa(ROOT_ID, "writer")

# Pendentes
result = gapi("drive", "create-folder", "Pendentes", "--parent", ROOT_ID)
PENDENTES_ID = result["id"]
print(f"  ✅ Pendentes: {PENDENTES_ID}")
share_with_sa(PENDENTES_ID, "writer")

# Processados
result = gapi("drive", "create-folder", "Processados", "--parent", ROOT_ID)
PROCESSADOS_ID = result["id"]
print(f"  ✅ Processados: {PROCESSADOS_ID}")
share_with_sa(PROCESSADOS_ID, "writer")

# ═══════════════════════════════════════════════════
# PASSO 2: Criar planilha Google Sheets
# ═══════════════════════════════════════════════════
print("\n═══ PASSO 2: Criando planilha Google Sheets ═══")

result = gapi("sheets", "create", "--title", "Clientes-Assessor-Teste")
PLANILHA_ID = result["spreadsheetId"]
print(f"  ✅ Planilha: {PLANILHA_ID}")
share_with_sa(PLANILHA_ID, "writer")

# Renomear Sheet1 → Clientes
print("  [*] Configurando abas...")
# Usamos a API Python direta pra renomear abas e criar a segunda
script = f"""
import json, sys
sys.path.insert(0, '/opt/data/skills/productivity/google-workspace/scripts')
from google_api import get_credentials, get_service

creds = get_credentials()
sheets = get_service('sheets', 'v4', creds)

SPREADSHEET_ID = '{PLANILHA_ID}'

# Pega info da planilha
info = sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
sheet1_id = info['sheets'][0]['properties']['sheetId']

# Renomeia Sheet1 → Clientes
sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={{
    'requests': [
        {{'updateSheetProperties': {{
            'properties': {{'sheetId': sheet1_id, 'title': 'Clientes'}},
            'fields': 'title'
        }}}},
        {{'addSheet': {{
            'properties': {{'title': 'Registros'}}
        }}}}
    ]
}}).execute()
print('✅ Abas configuradas: Clientes + Registros')
"""
subprocess.run(
    ["/opt/data/venvs/google/bin/python", "-c", script],
    capture_output=True, text=True, timeout=15
)
print("  ✅ Abas criadas")

# Popular aba Clientes com cabeçalho + 3 clientes
print("  [*] Populando aba Clientes...")
clientes_data = [
    ["ID", "Status", "Nome", "Telefone", "Vocativo", "Tom de Voz", "Instrucoes", "Status Envio", "Ultimo Resumo"],
    ["CPF-JOAO", "Envio Ativo", "Joao Silva", "557998423338", "Joao", "formal e objetivo", "Cliente conservador, foco em renda fixa", False, "Mes passado: 118% do CDI, RV Brasil puxou resultado."],
    ["CPF-MARIA", "Envio Ativo", "Maria Oliveira", "557998423338", "Maria", "proximo e empatico", "Cliente arrojada, gosta de acoes", False, "Mes passado: 95% do CDI, Multimercados sofreram."],
    ["CPF-CARLOS", "Envio Pausado", "Carlos Pereira", "557998423338", "Carlos", "consultivo e transparente", "Cliente em ferias. Retomar contato mes que vem.", False, "Sem historico"],
]
# Usa o endpoint sheets update
values_json = json.dumps(clientes_data)
subprocess.run(
    GAPI.split() + ["sheets", "update", PLANILHA_ID, "Clientes!A1:I4", "--values", values_json],
    capture_output=True, text=True, timeout=15
)
print("  ✅ 3 clientes inseridos (Joao, Maria, Carlos)")

# Popular aba Registros com cabeçalho
registros_data = [
    ["Data/Hora", "ID_Relatorio", "Nome_Cliente", "Status", "Detalhes"],
]
values_json = json.dumps(registros_data)
subprocess.run(
    GAPI.split() + ["sheets", "update", PLANILHA_ID, "Registros!A1:E1", "--values", values_json],
    capture_output=True, text=True, timeout=15
)
print("  ✅ Aba Registros pronta")

# ═══════════════════════════════════════════════════
# PASSO 3: Criar Google Docs de personalizacao
# ═══════════════════════════════════════════════════
print("\n═══ PASSO 3: Criando Google Docs ═══")

result = gapi("docs", "create", "--title", "Personalizacao-Assessor-Teste")
DOC_PERSONALIZACAO_ID = result["documentId"]
print(f"  ✅ Docs: {DOC_PERSONALIZACAO_ID}")
share_with_sa(DOC_PERSONALIZACAO_ID, "writer")

# Popular o Docs com conteúdo
conteudo = """MANUAL DE ESTILO DO ASSESSOR - TESTE

IDENTIDADE:
- Consultor de investimentos senior, acessivel mas profissional.
- Linguagem clara, sem jargoes excessivos.

ASSINATURA:
- Sempre encerrar com "Abraco!" ou "Estou por aqui!".
- Nunca usar "Att." ou "Cordialmente".

DIFERENCIAL:
- Explica conceitos financeiros de forma simples.
- Usa analogias do dia a dia para ilustrar.

PREFERENCIA:
- Mensagens de ate 5 linhas no WhatsApp.
- Maximo 3 emojis por mensagem.
- *negrito* para numeros e indicadores.
- _italico_ para nomes de relatorios.

CLIENTES:
- Clientes mais velhos: tratamento "Dona/Seu".
- Clientes jovens: tom mais descontraido.
- Sempre mencionar o cenario macro quando relevante.
"""
subprocess.run(
    GAPI.split() + ["docs", "append", DOC_PERSONALIZACAO_ID, "--text", conteudo],
    capture_output=True, text=True, timeout=15
)
print("  ✅ Conteudo inserido no Docs")

# ═══════════════════════════════════════════════════
# PASSO 4: Subir PDFs de teste na pasta Pendentes
# ═══════════════════════════════════════════════════
print("\n═══ PASSO 4: Subindo PDFs de teste ═══")

# Gera PDFs
from gerar_pdf_teste import gerar_pdf_cliente
pdfs = [
    ("Joao Silva", "/tmp/joao_silva.pdf"),
    ("Maria Oliveira", "/tmp/maria_oliveira.pdf"),
]
for nome, path in pdfs:
    gerar_pdf_cliente(nome, path)
    # Upload via GAPI
    result = gapi("drive", "upload", path, "--name", f"XPerformance_{nome.replace(' ', '_')}.pdf", "--parent", PENDENTES_ID)
    if result and result.get("status") == "uploaded":
        print(f"  ✅ PDF {nome} → Drive ({result['id']})")
    else:
        print(f"  ❌ Falha upload {nome}")

# ═══════════════════════════════════════════════════
# PASSO 5: Criar .env para o teste
# ═══════════════════════════════════════════════════
print("\n═══ PASSO 5: Salvando .env de teste ═══")

# Lê o JSON da service account
with open("/opt/data/Agemini/conectores/credenciais/service_account.json") as f:
    sa_json = json.dumps(json.load(f))

env_content = f"""# ═══════════════════════════════════════════
# TESTE - Augmentacao de Assessores
# Gerado automaticamente em {time.strftime('%Y-%m-%d %H:%M')}
# ═══════════════════════════════════════════

ASSESSORES_ATIVOS=1
ENVIOS_POR_EXECUCAO=3

ASSESSOR_1_NOME="Assessor XP Teste"
ASSESSOR_1_GEMINI_API_KEY=""
ASSESSOR_1_GOOGLE_CREDENTIALS_JSON='{sa_json}'
ASSESSOR_1_ID_PASTA_PENDENTES="{PENDENTES_ID}"
ASSESSOR_1_ID_PASTA_PROCESSADOS="{PROCESSADOS_ID}"
ASSESSOR_1_ID_PLANILHA_CLIENTES="{PLANILHA_ID}"
ASSESSOR_1_ID_DOC_PERSONALIZACAO="{DOC_PERSONALIZACAO_ID}"
ASSESSOR_1_NOME_ABA_CLIENTES="Clientes"
ASSESSOR_1_NOME_ABA_LOGS="Registros"
ASSESSOR_1_WHATSAPP_SERVICE_URL="http://localhost:3100"
"""

env_path = "/opt/data/augmentacao-assessores/.env"
with open(env_path, "w") as f:
    f.write(env_content)
print(f"  ✅ .env salvo em {env_path}")

# ═══════════════════════════════════════════════════
# RESUMO
# ═══════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  ✅ ESTRUTURA CRIADA NO GOOGLE DRIVE")
print("=" * 60)
print(f"""
  📁 Pasta raiz:       {ROOT_ID}
     ├── 📂 Pendentes:        {PENDENTES_ID}
     │   ├── XPerformance_Joao_Silva.pdf
     │   └── XPerformance_Maria_Oliveira.pdf
     └── 📂 Processados:      {PROCESSADOS_ID}

  📊 Planilha:          {PLANILHA_ID}
     ├── Aba Clientes  (3 clientes + cabecalho)
     └── Aba Registros (cabecalho)

  📄 Docs Personalizacao: {DOC_PERSONALIZACAO_ID}

  🔑 Service Account:   {SERVICE_ACCOUNT_EMAIL}
     (compartilhado como writer em todos os recursos)

  ⚡ Pronto para rodar:  python3 test_pipeline_drive.py
""")
