const { 
    default: makeWASocket, 
    useMultiFileAuthState, 
    DisconnectReason,
    fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const http = require('http');

const PASTA_COFRE = path.join(__dirname, 'auth_info_baileys');
const ARQUIVO_CONFIG = path.join(__dirname, 'grupo_config.json');

// Garante que a pasta do cofre existe
if (!fs.existsSync(PASTA_COFRE)) {
    fs.mkdirSync(PASTA_COFRE, { recursive: true });
}

let sock = null;
let estaConectado = false;
let gruposEncontrados = [];
let jidGrupoAlvo = null;
let ultimoQr = null;

// Carrega JID do grupo se já salvo
if (fs.existsSync(ARQUIVO_CONFIG)) {
    try {
        const cfg = JSON.parse(fs.readFileSync(ARQUIVO_CONFIG, 'utf8'));
        jidGrupoAlvo = cfg.jidGrupo || null;
    } catch (e) {}
}

async function iniciarBotWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(PASTA_COFRE);
    const { version } = await fetchLatestBaileysVersion();

    console.log("==================================================");
    console.log("🚀 INICIANDO CONECTOR WHATSAPP (BAILEYS)");
    console.log("Nome do Aparelho: Achadinhos da Família");
    console.log("==================================================");

    sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        auth: state,
        browser: ['Achadinhos da Família', 'Chrome', '1.0.0'],
        syncFullHistory: false,
        markOnlineOnConnect: false
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            ultimoQr = qr;
            console.log("\n📲 ESCANEIE O QR CODE ABAIXO NO SEU CELULAR:");
            console.log("Vá em: WhatsApp > Aparelhos Conectados > Conectar um Aparelho\n");
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            estaConectado = false;
            const statusCode = (lastDisconnect?.error)?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log(`⚠️ Conexão fechada (${statusCode}). Reconectando: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(iniciarBotWhatsApp, 3000);
            }
        } else if (connection === 'open') {
            estaConectado = true;
            ultimoQr = null;
            console.log("\n✅ SUCESSO! WHATSAPP CONECTADO COM SUCESSO!");
            console.log("Aparelho ativo como: Achadinhos da Família");

            // Busca os grupos do usuário
            try {
                const chats = await sock.groupFetchAllParticipating();
                gruposEncontrados = Object.values(chats).map(g => ({
                    id: g.id,
                    subject: g.subject
                }));
                console.log(`\n📋 Grupos encontrados: ${gruposEncontrados.length}`);
                
                // Procura o grupo "Achadiinhos da Família" ou "Achadinhos da Família"
                const grupoAlvo = gruposEncontrados.find(g => 
                    g.subject.toLowerCase().includes('achadiinhos da fam') ||
                    g.subject.toLowerCase().includes('achadinhos da fam')
                );

                if (grupoAlvo) {
                    jidGrupoAlvo = grupoAlvo.id;
                    fs.writeFileSync(ARQUIVO_CONFIG, JSON.stringify({
                        nomeGrupo: grupoAlvo.subject,
                        jidGrupo: grupoAlvo.id
                    }, null, 2));
                    console.log(`🎯 Grupo Alvo Identificado e Conectado: "${grupoAlvo.subject}" (${grupoAlvo.id})`);
                } else {
                    console.log("ℹ️ Grupos disponíveis:");
                    gruposEncontrados.slice(0, 10).forEach(g => console.log(`   - ${g.subject} (${g.id})`));
                }
            } catch (err) {
                console.log("Erro ao listar grupos:", err.message);
            }
        }
    });
}

// Inicia servidor HTTP local na porta 3333 para receber pedidos do robô Python
const server = http.createServer(async (req, res) => {
    res.setHeader('Content-Type', 'application/json');

    if (req.method === 'GET' && req.url === '/status') {
        res.writeHead(200);
        return res.end(JSON.stringify({
            conectado: estaConectado,
            jidGrupo: jidGrupoAlvo,
            qr: ultimoQr,
            grupos: gruposEncontrados
        }));
    }

    if (req.method === 'POST' && req.url === '/enviar') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const dados = JSON.parse(body);
                const grupoDestino = dados.grupo || jidGrupoAlvo;
                const caminhoFoto = dados.foto;
                const legenda = dados.legenda;

                if (!estaConectado || !sock) {
                    res.writeHead(400);
                    return res.end(JSON.stringify({ erro: 'WhatsApp não está conectado' }));
                }

                if (!grupoDestino) {
                    res.writeHead(400);
                    return res.end(JSON.stringify({ erro: 'Grupo de destino não identificado' }));
                }

                let resultadoEnvio;
                if (caminhoFoto && fs.existsSync(caminhoFoto)) {
                    const bufferFoto = fs.readFileSync(caminhoFoto);
                    resultadoEnvio = await sock.sendMessage(grupoDestino, {
                        image: bufferFoto,
                        caption: String(legenda || '')
                    });
                    console.log(`📤 Oferta enviada com foto para: ${grupoDestino}`);
                } else {
                    resultadoEnvio = await sock.sendMessage(grupoDestino, {
                        text: String(legenda || '')
                    });
                    console.log(`📤 Oferta enviada com texto para: ${grupoDestino}`);
                }

                res.writeHead(200);
                return res.end(JSON.stringify({ sucesso: true, id: resultadoEnvio?.key?.id }));
            } catch (e) {
                console.error("❌ Erro no envio Baileys:", e);
                res.writeHead(500);
                return res.end(JSON.stringify({ sucesso: false, erro: e.message || String(e) }));
            }
        });
        return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ erro: 'Não encontrado' }));
});

const PORTA = 3333;
server.listen(PORTA, () => {
    console.log(`🌐 Servidor da API do Baileys rodando na porta ${PORTA}`);
    iniciarBotWhatsApp();
});
