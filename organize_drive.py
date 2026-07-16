"""Organiza Drive: move tudo para 'Assessor Teste'."""
import sys, json
sys.path.insert(0, '/opt/data/skills/productivity/google-workspace/scripts')
from google_api import get_credentials, build_service

creds = get_credentials()
drive = build_service('drive', 'v3')

ROOT_NAME = "Assessor Teste"
OLD_ROOT = "1BvHeFTRbUcJMkwyxwG7IzfJamnyhMKqG"
PLANILHA_ID = "1z_Sjv4nVDfR6nFtyvnI0RH4Q9a7wdn0frVKHVePJnyI"
DOCS_ID = "1AGidw_UQ2LDhnTOfAcbA92W8ArsN6Zr2ztwCFQO9Y58"

# 1. Criar ou encontrar "Assessor Teste"
print("Criando 'Assessor Teste'...")
r = drive.files().create(body={
    'name': ROOT_NAME,
    'mimeType': 'application/vnd.google-apps.folder'
}, fields='id').execute()
NEW_ROOT = r['id']
print(f"  ✅ {NEW_ROOT}")

# 2. Listar conteúdo da pasta antiga
print(f"\nConteudo da pasta antiga:")
results = drive.files().list(
    q=f"'{OLD_ROOT}' in parents and trashed=false",
    fields="files(id, name, mimeType)",
    pageSize=50
).execute()
items = results.get('files', [])

# 3. Mover cada item
for item in items:
    fid, name, mime = item['id'], item['name'], item['mimeType']
    emoji = "📂" if "folder" in mime else "📄"
    print(f"  Movendo {emoji} {name}...")
    try:
        drive.files().update(fileId=fid, addParents=NEW_ROOT,
            removeParents=OLD_ROOT, fields='id').execute()
        print(f"    ✅")
    except Exception as e:
        print(f"    ⚠️ {e}")

# 4. Adicionar planilha e docs à nova pasta
print(f"\nAdicionando planilha e docs...")
for fid, label in [(PLANILHA_ID, "Planilha"), (DOCS_ID, "Docs")]:
    try:
        drive.files().update(fileId=fid, addParents=NEW_ROOT, fields='id').execute()
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ⚠️ {label}: {e}")

# 5. Limpar pasta antiga
print(f"\nLimpando pasta antiga...")
try:
    drive.files().delete(fileId=OLD_ROOT).execute()
    print("  ✅ Removida")
except Exception as e:
    print(f"  ⚠️ {e}")

# 6. Estrutura final
print(f"\n{'='*50}")
print(f"  ESTRUTURA: {ROOT_NAME}")
print(f"{'='*50}")
results = drive.files().list(
    q=f"'{NEW_ROOT}' in parents and trashed=false",
    fields="files(id, name, mimeType)",
    pageSize=50
).execute()

PENDENTES_ID = PROCESSADOS_ID = None
for item in results.get('files', []):
    mime, name, fid = item['mimeType'], item['name'], item['id']
    if "folder" in mime:
        print(f"  📂 {name} ({fid})")
        if name == "Pendentes": PENDENTES_ID = fid
        elif name == "Processados": PROCESSADOS_ID = fid
        # Listar PDFs dentro
        subs = drive.files().list(
            q=f"'{fid}' in parents and trashed=false",
            fields="files(name)", pageSize=20
        ).execute()
        for s in subs.get('files', []):
            print(f"     └── 📄 {s['name']}")
    elif "spreadsheet" in mime:
        print(f"  📊 {name} ({fid})")
    elif "document" in mime:
        print(f"  📄 {name} ({fid})")

print(f"\n{'='*50}")
print(f"  NOVOS IDs:")
print(f"  PENDENTES = {PENDENTES_ID}")
print(f"  PROCESSADOS = {PROCESSADOS_ID}")
print(f"  PLANILHA = {PLANILHA_ID}")
print(f"  DOCS = {DOCS_ID}")
print(f"{'='*50}")
