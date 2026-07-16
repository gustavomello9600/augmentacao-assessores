"""
Configuração multi-assessor.

Cada assessor é definido por um prefixo nas variáveis de ambiente.
Exemplo para 2 assessores:

    ASSESSOR_1_NOME="João Silva"
    ASSESSOR_1_GEMINI_API_KEY="..."
    ASSESSOR_1_GOOGLE_CREDENTIALS_JSON='{...}'
    ASSESSOR_1_WHATSAPP_SERVICE_URL="http://localhost:3100"
    ASSESSOR_1_ID_PASTA_PENDENTES="..."
    ASSESSOR_1_ID_PASTA_PROCESSADOS="..."
    ASSESSOR_1_ID_PLANILHA_CLIENTES="..."
    ASSESSOR_1_ID_DOC_PERSONALIZACAO="..."

    ASSESSOR_2_NOME="Maria Oliveira"
    ASSESSOR_2_GEMINI_API_KEY="..."
    # ... etc

    ASSESSORES_ATIVOS="1,2"   # Quais executar (opcional, default: "1")
    ENVIOS_POR_EXECUCAO=8     # Limite global de envios (opcional)
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class AssessorConfig:
    """Configuração de um assessor específico."""

    def __init__(self, prefixo: str):
        self.prefixo = prefixo
        self.nome = self._env("NOME", f"Assessor {prefixo}")

        # Google Gemini
        self.gemini_api_key = self._env("GEMINI_API_KEY", "")
        self.gemini_model = self._env("GEMINI_MODEL", "gemini-3.1-flash-lite")

        # Google Cloud (opcional — pode vir como JSON string ou caminho de arquivo)
        self.google_credentials_json = os.environ.get(f"{prefixo}_GOOGLE_CREDENTIALS_JSON")

        # Google Drive
        self.id_pasta_pendentes = self._env("ID_PASTA_PENDENTES")
        self.id_pasta_processados = self._env("ID_PASTA_PROCESSADOS")
        self.id_doc_personalizacao = self._env("ID_DOC_PERSONALIZACAO", "")

        # Google Sheets
        self.id_planilha_clientes = self._env("ID_PLANILHA_CLIENTES")
        self.nome_aba_clientes = self._env("NOME_ABA_CLIENTES", "Clientes")
        self.nome_aba_logs = self._env("NOME_ABA_LOGS", "Registros")

        # WhatsApp via Baileys
        self.whatsapp_service_url = self._env("WHATSAPP_SERVICE_URL", "http://localhost:3100")

        # Limite de envios
        self.envios_por_execucao = int(os.environ.get("ENVIOS_POR_EXECUCAO", "8"))

    def _env(self, chave: str, default: Optional[str] = None) -> str:
        """Busca variável com prefixo do assessor."""
        valor = os.environ.get(f"{self.prefixo}_{chave}")
        if valor is None:
            if default is not None:
                return default
            raise ValueError(f"[{self.prefixo}] Variável {self.prefixo}_{chave} não definida")
        return valor

    def get_google_credentials(self) -> Optional[dict]:
        """Retorna as credenciais Google como dict, ou None se não encontradas."""
        if self.google_credentials_json:
            return json.loads(self.google_credentials_json)
        # Fallback: arquivo local
        cred_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "conectores/credenciais/service_account.json")
        if os.path.exists(cred_path):
            with open(cred_path) as f:
                return json.load(f)
        return None


def get_config() -> AssessorConfig:
    """
    Carrega a configuração para UM assessor (por job Cloud Run).
    
    Lê ASSESSOR_PREFIX do ambiente (default: ASSESSOR_1).
    Cada job define ASSESSOR_PREFIX=ASSESSOR_2, ASSESSOR_3, etc.
    """
    prefixo = os.environ.get("ASSESSOR_PREFIX", "ASSESSOR_1")
    return AssessorConfig(prefixo)
