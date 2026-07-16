"""
Cliente HTTP para o serviço Baileys (WhatsApp Web).

Substitui a integração Z-API por um bridge local Node.js usando Baileys.
O serviço Baileys expõe uma REST API simples nos mesmos moldes da Z-API,
facilitando a migração.

Endpoint esperados no serviço Baileys:
    GET  /phone-exists/{telefone}  → {"exists": bool, "lid": str}
    POST /send-text                → {"phone": str, "message": str}
    POST /send-document/pdf       → {"phone": str, "document": "data:application/pdf;base64,...", "fileName": str}
"""

import base64
import os
import subprocess
import time
import signal
import requests
from typing import Optional


class BaileysManager:
    """Gerencia o ciclo de vida do processo Baileys (liga → usa → desliga).

    Inicia o serviço Node.js como subprocesso, aguarda a conexão
    WhatsApp (reutilizando sessão salva, sem QR na segunda execução),
    e encerra graciosamente ao final da pipeline.

    Uso:
        manager = BaileysManager(session_dir="./sessions/assessor1", porta=3100)
        manager.iniciar()
        client = manager.client
        # ... usa client.send_pdf_and_text(...) ...
        manager.encerrar()
    """

    def __init__(self, session_dir: str = "./sessions/assessor1", porta: int = 3100):
        self.session_dir = session_dir
        self.porta = porta
        self.proc: Optional[subprocess.Popen] = None
        self.client = BaileysClient(base_url=f"http://localhost:{porta}")

    def _health(self) -> dict:
        """Consulta o /health do serviço Baileys."""
        try:
            r = requests.get(f"http://localhost:{self.porta}/health", timeout=2)
            return r.json()
        except Exception:
            return {"status": "offline"}

    def iniciar(self, timeout: int = 30) -> bool:
        """
        Inicia o processo Node.js do Baileys e aguarda conexão WhatsApp.

        Se a sessão existe (segunda execução em diante), conecta em 3-10s sem QR.
        Se for primeira execução (sem sessão), vai gerar QR code e precisa de scan.

        Returns:
            True se conectou, False se timeout.
        """
        # Cria diretório de sessão se não existir
        os.makedirs(self.session_dir, exist_ok=True)

        # Localiza o baileys_service.js (resolve path relativo ao projeto)
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        js_path = os.path.join(script_dir, "baileys_service.js")
        if not os.path.exists(js_path):
            js_path = os.path.join(os.getcwd(), "baileys_service.js")

        print(f"[BaileysManager] Iniciando serviço na porta {self.porta}...")
        print(f"[BaileysManager] Sessão: {self.session_dir}")

        self.proc = subprocess.Popen(
            ["node", js_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            env={
                **os.environ,
                "PORT": str(self.porta),
                "SESSION_DIR": os.path.abspath(self.session_dir),
                "ASSESSOR_NOME": os.environ.get("ASSESSOR_1_NOME", "Assessor XP"),
            },
        )

        # Aguarda o servidor HTTP subir
        print("[BaileysManager] Aguardando servidor HTTP...")
        for _ in range(5):
            try:
                requests.get(f"http://localhost:{self.porta}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            print("[BaileysManager] ⚠️ Servidor HTTP não respondeu")

        # Aguarda conexão WhatsApp (reutiliza sessão se existir)
        sessao_existe = os.path.exists(
            os.path.join(self.session_dir, "creds.json")
        )
        if sessao_existe:
            print("[BaileysManager] Sessão encontrada. Conectando sem QR...")

        for i in range(timeout):
            health = self._health()
            status = health.get("status", "offline")

            if status == "connected":
                print(f"[BaileysManager] ✅ WhatsApp conectado! (levou {i+1}s)")
                return True

            if status == "awaiting_qr":
                if sessao_existe:
                    print("[BaileysManager] ⚠️ Sessão expirada, precisa de novo QR.")
                else:
                    print("[BaileysManager] 📱 Primeira execução — escaneie o QR code.")
                qr_path = os.path.join(os.getcwd(), "qr_code.png")
                self._salvar_qr(qr_path)
                print(f"[BaileysManager] 📷 QR salvo em {qr_path}")
                print("[BaileysManager] ⚠️ Aguardando scan... (timeout em breve)")

                # Aguarda mais 55s além dos já gastos
                for j in range(timeout - i):
                    health = self._health()
                    if health.get("status") == "connected":
                        print(f"[BaileysManager] ✅ WhatsApp conectado via QR!")
                        return True
                    time.sleep(1)
                return False

            time.sleep(1)

        print(f"[BaileysManager] ❌ Timeout ({timeout}s). WhatsApp não conectou.")
        return False

    def encerrar(self):
        """Encerra o processo Baileys graciosamente (salva sessão)."""
        if not self.proc:
            return

        print("[BaileysManager] Encerrando serviço Baileys...")
        try:
            self.proc.send_signal(signal.SIGTERM)
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        print("[BaileysManager] ✅ Serviço encerrado.")

    def _salvar_qr(self, output_path: str):
        """Busca o QR code do serviço e salva como PNG."""
        try:
            r = requests.get(f"http://localhost:{self.porta}/qr", timeout=3)
            data = r.json()
            if "qr" in data:
                b64 = data["qr"].split(",", 1)[-1] if "," in data["qr"] else data["qr"]
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(b64))
        except Exception:
            pass

    def __enter__(self):
        self.iniciar()
        return self

    def __exit__(self, *args):
        self.encerrar()


class BaileysClient:
    """Cliente HTTP para o serviço Baileys (substituto da Z-API)."""

    def __init__(self, base_url: str = "http://localhost:3100", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get(self, path: str) -> dict:
        resp = self.session.get(f"{self.base_url}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: dict) -> dict:
        resp = self.session.post(f"{self.base_url}{path}", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ── Métodos equivalentes aos da Z-API ──────────────────────────

    def phone_exists(self, telefone: str) -> Optional[str]:
        """
        Verifica se o número tem WhatsApp e retorna o @lid.
        Retorna None se o número não existir no WhatsApp.

        Args:
            telefone: Número no formato DDI+DDD+Número (ex: 5511999999999)

        Returns:
            @lid do WhatsApp ou None
        """
        try:
            dados = self._get(f"/phone-exists/{telefone}")
            if dados.get("exists"):
                lid = dados.get("lid")
                if lid:
                    print(f"    [+] @lid encontrado: {lid}")
                    return lid
                print(f"    [!] @lid não retornado. Usando telefone como fallback: {telefone}")
                return telefone
            else:
                print(f"    [-] O número {telefone} não possui WhatsApp.")
                return None
        except Exception as e:
            print(f"    [-] Erro ao verificar número: {e}")
            return None

    def send_text(self, phone: str, message: str) -> bool:
        """
        Envia mensagem de texto via WhatsApp.

        Args:
            phone: Identificador do destinatário (@lid ou telefone)
            message: Texto da mensagem (aceita *negrito*, _itálico_, etc.)

        Returns:
            True se enviado com sucesso
        """
        try:
            print(f"    [*] Enviando mensagem para: {phone}...")
            self._post("/send-text", {"phone": phone, "message": message})
            print("    [+] MENSAGEM ENTREGUE COM SUCESSO! 🚀")
            return True
        except Exception as e:
            print(f"    [-] Erro ao enviar mensagem: {e}")
            return False

    def send_pdf_document(self, phone: str, pdf_path: str, file_name: str) -> bool:
        """
        Envia documento PDF via WhatsApp.

        Args:
            phone: Identificador do destinatário (@lid ou telefone)
            pdf_path: Caminho local do arquivo PDF
            file_name: Nome do arquivo a exibir

        Returns:
            True se enviado com sucesso
        """
        try:
            with open(pdf_path, "rb") as f:
                pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

            print(f"    [*] Enviando PDF '{file_name}' para: {phone}...")
            self._post("/send-document/pdf", {
                "phone": phone,
                "document": f"data:application/pdf;base64,{pdf_base64}",
                "fileName": file_name,
            })
            print("    [+] PDF enviado com sucesso! 📎")
            return True
        except Exception as e:
            print(f"    [-] Erro ao enviar PDF: {e}")
            return False

    def send_pdf_and_text(self, telefone: str, pdf_path: str, pdf_name: str, message: str) -> bool:
        """
        Fluxo completo: valida número → envia PDF → envia mensagem de texto.

        Args:
            telefone: Número do cliente
            pdf_path: Caminho do PDF local
            pdf_name: Nome do arquivo
            message: Mensagem de texto formatada

        Returns:
            True apenas se AMBOS forem bem-sucedidos
        """
        # 1. Valida o número (obtém @lid)
        identificador = self.phone_exists(telefone)
        if not identificador:
            print(f"    [-] Não foi possível validar o número {telefone}. Envio cancelado.")
            return False

        # 2. Envia o PDF
        if not self.send_pdf_document(identificador, pdf_path, pdf_name):
            return False

        # 3. Envia a mensagem de texto
        return self.send_text(identificador, message)
