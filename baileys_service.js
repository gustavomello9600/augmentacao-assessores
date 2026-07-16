/**
 * Serviço Baileys — WhatsApp Web Gateway (v2)
 * ===========================================
 *
 * Substituto local da Z-API. Usa @whiskeysockets/baileys para conectar
 * diretamente ao WhatsApp Web, sem custos de API de terceiros.
 *
 * Endpoints REST:
 *   GET  /health                  → status do serviço
 *   GET  /qr                       → QR code como PNG base64 (para escanear)
 *   GET  /phone-exists/:phone     → verifica se número tem WhatsApp
 *   POST /send-text               → envia mensagem de texto
 *   POST /send-document/pdf       → envia documento PDF
 *
 * Autenticação:
 *   GET /qr → retorna QR code PNG em base64 para escanear no WhatsApp
 *   A sessão é salva em disco e reutilizada.
 *
 * Uso:
 *   npm install qrcode && node baileys_service.js
 */

const express = require('express');
const { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const QRCode = require('qrcode');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3100;
const SESSION_DIR = process.env.SESSION_DIR || path.join(__dirname, 'baileys_sessions');
const ASSESSOR_NOME = process.env.ASSESSOR_NOME || 'Assessor';

const app = express();
app.use(express.json({ limit: '50mb' }));

// ── Estado global ──────────────────────────────────
let sock = null;
let isConnected = false;
let qrCodeData = null;       // QR code string atual
let qrCodeImage = null;      // QR code PNG base64
let reconnectAttempts = 0;
const MAX_RECONNECT = 10;

// ── Conexão WhatsApp ────────────────────────────────
async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_DIR);
    const { version } = await fetchLatestBaileysVersion();

    sock = makeWASocket({
        auth: state,
        version,
        defaultQueryTimeoutMs: 60_000,
        connectTimeoutMs: 60_000,
        qrTimeout: 60_000,
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        // QR Code disponível
        if (qr) {
            qrCodeData = qr;
            QRCode.toDataURL(qr, { width: 400, margin: 2 })
                .then(dataUrl => {
                    qrCodeImage = dataUrl;
                    console.log(`[${ASSESSOR_NOME}] 📱 QR Code gerado! Acesse GET /qr para escanear.`);
                    // Também imprime ASCII no console
                    QRCode.toString(qr, { type: 'terminal', small: true }, (err, ascii) => {
                        if (!err) console.log('\n' + ascii + '\n');
                    });
                })
                .catch(err => console.error('Erro ao gerar QR:', err));
        }

        if (connection === 'open') {
            isConnected = true;
            qrCodeData = null;
            qrCodeImage = null;
            reconnectAttempts = 0;
            console.log(`[${ASSESSOR_NOME}] ✅ WhatsApp conectado!`);
        }

        if (connection === 'close') {
            isConnected = false;
            qrCodeData = null;
            qrCodeImage = null;

            const statusCode = lastDisconnect?.error instanceof Boom
                ? lastDisconnect?.error?.output?.statusCode
                : null;

            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

            console.log(`[${ASSESSOR_NOME}] ⚠️ Conexão fechada (code: ${statusCode}). Reconectar: ${shouldReconnect}`);

            if (shouldReconnect && reconnectAttempts < MAX_RECONNECT) {
                reconnectAttempts++;
                const delay = Math.min(3000 * reconnectAttempts, 30000);
                console.log(`[${ASSESSOR_NOME}] 🔄 Tentativa ${reconnectAttempts}/${MAX_RECONNECT} em ${delay / 1000}s...`);
                setTimeout(connectToWhatsApp, delay);
            } else {
                console.log(`[${ASSESSOR_NOME}] ❌ Sessão encerrada ou limite de tentativas. Delete ${SESSION_DIR} para reautenticar.`);
            }
        }
    });

    // Timeout: se não conectar em 2 min, segue com o servidor
    setTimeout(() => {
        if (!isConnected && !qrCodeData) {
            console.log(`[${ASSESSOR_NOME}] ⏰ Timeout de conexão. Servidor segue respondendo health checks.`);
        }
    }, 120_000);
}

// ── REST API ────────────────────────────────────────

// Health check
app.get('/health', (_req, res) => {
    res.json({
        status: isConnected ? 'connected' : (qrCodeData ? 'awaiting_qr' : 'disconnected'),
        has_qr: !!qrCodeData,
        assessor: ASSESSOR_NOME,
        reconnect_attempts: reconnectAttempts,
        timestamp: new Date().toISOString(),
    });
});

// QR Code como imagem PNG (base64)
app.get('/qr', (_req, res) => {
    if (!qrCodeImage) {
        return res.status(404).json({
            error: 'QR Code não disponível',
            hint: isConnected ? 'WhatsApp já está conectado.' : 'Aguardando geração do QR code...',
            status: isConnected ? 'connected' : 'waiting',
        });
    }
    res.json({ qr: qrCodeImage, type: 'image/png', encoding: 'base64' });
});

// Verificar se número tem WhatsApp
app.get('/phone-exists/:phone', async (req, res) => {
    if (!isConnected || !sock) {
        return res.status(503).json({ exists: false, error: 'WhatsApp não conectado' });
    }

    const phone = req.params.phone;
    try {
        const [result] = await sock.onWhatsApp(phone);
        if (result && result.exists) {
            console.log(`[${ASSESSOR_NOME}] 📱 Número ${phone} existe`);
            res.json({ exists: true, lid: result.jid, phone });
        } else {
            console.log(`[${ASSESSOR_NOME}] ❌ Número ${phone} NÃO encontrado`);
            res.json({ exists: false, phone });
        }
    } catch (err) {
        console.error(`[${ASSESSOR_NOME}] Erro ao verificar ${phone}:`, err.message);
        res.status(500).json({ exists: false, error: err.message });
    }
});

// Enviar mensagem de texto
app.post('/send-text', async (req, res) => {
    if (!isConnected || !sock) {
        return res.status(503).json({ error: 'WhatsApp não conectado' });
    }
    const { phone, message } = req.body;
    if (!phone || !message) {
        return res.status(400).json({ error: 'phone e message são obrigatórios' });
    }
    try {
        const jid = phone.includes('@s.whatsapp.net') ? phone : `${phone}@s.whatsapp.net`;
        await sock.sendMessage(jid, { text: message });
        console.log(`[${ASSESSOR_NOME}] ✅ Mensagem enviada para ${phone}`);
        res.json({ success: true, phone });
    } catch (err) {
        console.error(`[${ASSESSOR_NOME}] Erro ao enviar texto:`, err.message);
        res.status(500).json({ error: err.message });
    }
});

// Enviar documento PDF
app.post('/send-document/pdf', async (req, res) => {
    if (!isConnected || !sock) {
        return res.status(503).json({ error: 'WhatsApp não conectado' });
    }
    const { phone, document, fileName } = req.body;
    if (!phone || !document || !fileName) {
        return res.status(400).json({ error: 'phone, document e fileName são obrigatórios' });
    }
    try {
        const jid = phone.includes('@s.whatsapp.net') ? phone : `${phone}@s.whatsapp.net`;
        const base64Data = document.replace(/^data:application\/pdf;base64,/, '');
        const buffer = Buffer.from(base64Data, 'base64');
        await sock.sendMessage(jid, { document: buffer, fileName, mimetype: 'application/pdf' });
        console.log(`[${ASSESSOR_NOME}] ✅ PDF '${fileName}' enviado para ${phone}`);
        res.json({ success: true, fileName, phone });
    } catch (err) {
        console.error(`[${ASSESSOR_NOME}] Erro ao enviar PDF:`, err.message);
        res.status(500).json({ error: err.message });
    }
});

// ── Inicialização ───────────────────────────────────
async function start() {
    console.log(`\n[${ASSESSOR_NOME}] 🚀 Serviço Baileys v2 — porta ${PORT}`);
    console.log(`[${ASSESSOR_NOME}] 📁 Sessão: ${SESSION_DIR}`);
    if (!fs.existsSync(SESSION_DIR)) fs.mkdirSync(SESSION_DIR, { recursive: true });

    connectToWhatsApp().catch(err => console.error(`[${ASSESSOR_NOME}] Erro fatal:`, err));

    app.listen(PORT, () => {
        console.log(`[${ASSESSOR_NOME}] ✅ HTTP OK → http://localhost:${PORT}`);
        console.log(`[${ASSESSOR_NOME}] 📡 Endpoints: /health /qr /phone-exists/:phone /send-text /send-document/pdf\n`);
    });
}

start();
