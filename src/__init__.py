"""
🚀 Augmentação de Assessores — Pipeline de Relatórios XP

Automação que:
1. Monitora Google Drive por novos relatórios PDF (XPerformance)
2. Identifica clientes via integração com Google Sheets
3. Gera mensagens personalizadas de WhatsApp usando Gemini
4. Envia relatórios para clientes via Baileys (WhatsApp Web)
5. Registra tudo em logs no Google Sheets

Configuração multi-assessor: cada assessor tem seu próprio conjunto de
variáveis de ambiente, facilitando a adição de novos assessores.

Uso:
    python main.py
"""

__version__ = "1.0.0"
