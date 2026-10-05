import os
import sys
import json
import time
import threading
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Configurações básicas
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "7709565576:AAHGp5jJ90vQe-3xX8k2Uv1Yg_98Yv8z9k8")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "5960174121")

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Achadinhos da Família - Robô Nuvem</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 80vh;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 30px 40px;
            max-width: 550px;
            width: 100%;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
            text-align: center;
        }
        h1 { margin-top: 0; color: #ffeb3b; }
        .status-badge {
            display: inline-block;
            background: #4caf50;
            color: #fff;
            padding: 8px 18px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 20px;
        }
        p { font-size: 16px; line-height: 1.6; color: #e0e0e0; }
        .uptime-info {
            background: rgba(0, 0, 0, 0.2);
            padding: 12px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="status-badge">🟢 SERVIÇO EM NUVEM ONLINE 24/7</div>
        <h1>Achadinhos da Família 🛍️</h1>
        <p>Robô de Monitoramento e Automação de Afiliados Shopee ativo na nuvem!</p>
        <div class="uptime-info">
            Rota de Monitoramento (UptimeRobot): <b>/ping</b><br>
            Status do Servidor: <b>Operacional</b>
        </div>
    </div>
</body>
</html>
"""
import gc
import subprocess

def iniciar_servico_baileys():
    time.sleep(2)
    # Se o Baileys já estiver rodando (iniciado pelo start.sh), não inicia outro processo
    try:
        r = requests.get("http://127.0.0.1:3333/status", timeout=2)
        if r.status_code == 200:
            print("✅ [NUVEM] Baileys já está ativo na porta 3333.")
            return
    except Exception:
        pass

    caminho_baileys = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatsapp_baileys")
    index_file = os.path.join(caminho_baileys, "index.js")
    node_modules = os.path.join(caminho_baileys, "node_modules")
    
    # Se estiver rodando na nuvem e o node_modules não estiver presente, instala sozinho
    if not os.path.exists(node_modules) and os.path.exists(caminho_baileys):
        try:
            print("📦 [NUVEM] Instalando dependências do Baileys via npm...")
            subprocess.run(["npm", "install", "--production"], cwd=caminho_baileys, check=True)
            print("✅ [NUVEM] Dependências do Baileys instaladas com sucesso!")
        except Exception as e:
            print(f"⚠️ [NUVEM] Aviso ao instalar npm: {e}")

    if os.path.exists(index_file):
        try:
            print("🚀 [NUVEM] Inicializando Conector WhatsApp Baileys em background...")
            env = os.environ.copy()
            env["NODE_OPTIONS"] = "--max-old-space-size=128"
            subprocess.Popen(["node", "index.js"], cwd=caminho_baileys, env=env)
            print("✅ [NUVEM] Processo Baileys WhatsApp ativo na porta 3333!")
        except Exception as e:
            print(f"⚠️ [NUVEM] Erro ao iniciar Baileys: {e}")

# Inicia o conector WhatsApp Baileys em segundo plano
threading.Thread(target=iniciar_servico_baileys, daemon=True).start()

def iniciar_radar_background():
    # Aguarda 10 segundos para dar tempo do Baileys subir e conectar
    time.sleep(10)
    while True:
        try:
            from core.radar_shopee import varrer_canais, carregar_status_radar
            st = carregar_status_radar()
            if st.get("envios_ativos", True):
                varrer_canais()
            else:
                print("⏸️ [RADAR] Envios automáticos pausados pelo usuário no painel.")
        except Exception as e:
            print(f"Erro no loop do radar: {e}")
        gc.collect()
        
        try:
            from core.radar_shopee import carregar_status_radar
            st = carregar_status_radar()
            delay = st.get("proxima_varredura_segundos", 180)
        except Exception:
            delay = 180
            
        time.sleep(delay)

# Inicia o radar em segundo plano na nuvem
threading.Thread(target=iniciar_radar_background, daemon=True).start()

@app.route("/varrer-agora")
def varrer_agora():
    try:
        from core.radar_shopee import varrer_canais
        novas = varrer_canais()
        gc.collect()
        return jsonify({
            "status": "sucesso",
            "novas_ofertas": len(novas),
            "mensagem": f"{len(novas)} itens da Shopee processados e enviados!"
        }), 200
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/api/pausar-envios", methods=["GET", "POST"])
def pausar_envios():
    try:
        from core.radar_shopee import salvar_status_radar
        salvar_status_radar({"envios_ativos": False})
        return jsonify({"status": "pausado", "envios_ativos": False, "mensagem": "Envios pausados com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/retomar-envios", methods=["GET", "POST"])
def retomar_envios():
    try:
        from core.radar_shopee import salvar_status_radar
        salvar_status_radar({"envios_ativos": True})
        return jsonify({"status": "ativo", "envios_ativos": True, "mensagem": "Envios retomados com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/toggle-envios", methods=["GET", "POST"])
def toggle_envios():
    try:
        from core.radar_shopee import carregar_status_radar, salvar_status_radar
        st = carregar_status_radar()
        novo = not st.get("envios_ativos", True)
        salvar_status_radar({"envios_ativos": novo})
        return jsonify({"status": "ok", "envios_ativos": novo}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/whatsapp-status")
def whatsapp_status():
    try:
        from core.whatsapp_baileys_sender import verificar_conexao_baileys
        status = verificar_conexao_baileys()
        return jsonify({
            "status_baileys": status,
            "dispositivo": "Achadinhos da Família",
            "timestamp": int(time.time())
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/limpar-cache")
def limpar_cache():
    try:
        from core.radar_shopee import faxina_pastas_temporarias
        faxina_pastas_temporarias()
        gc.collect()
        return jsonify({"status": "sucesso", "mensagem": "Cache de mídia e memória limpos com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/logs")
def api_logs():
    historico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "historico_envios.json")
    if os.path.exists(historico_path):
        try:
            with open(historico_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
            return jsonify({"logs": logs, "total": len(logs)})
        except Exception:
            pass
    return jsonify({"logs": [], "total": 0})

@app.route("/api/limpar-logs", methods=["GET", "POST"])
def api_limpar_logs():
    historico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "historico_envios.json")
    try:
        with open(historico_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return jsonify({"status": "sucesso", "mensagem": "Histórico de logs limpo!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/status-radar")
def api_status_radar():
    total_fila = 0
    fila_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fila", "ofertas_prontas.json")
    if os.path.exists(fila_path):
        try:
            with open(fila_path, "r", encoding="utf-8") as f:
                total_fila = len(json.load(f))
        except Exception:
            pass

    status_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "status_radar.json")
    dados = {
        "ultima_varredura": "Ativo agora",
        "status": "online",
        "envios_ativos": True,
        "canais_ativos": 5,
        "total_fila_reserva": total_fila,
        "novos_ultimo_ciclo": 0,
        "proxima_varredura_segundos": 180 if total_fila > 10 else 300
    }
    if os.path.exists(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                carregado = json.load(f)
                dados.update(carregado)
        except Exception:
            pass
            
    dados["total_fila_reserva"] = total_fila
    return jsonify(dados)

HTML_WHATSAPP = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel Shopee Nuvem - Achadinhos da Família</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            color: #fff;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            box-sizing: border-box;
        }
        .container {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 25px;
            max-width: 640px;
            width: 100%;
            text-align: center;
            box-shadow: 0 12px 40px rgba(0,0,0,0.5);
        }
        h1 { margin: 0 0 8px 0; font-size: 24px; color: #ff9800; }
        p { color: #cfd8dc; font-size: 14px; line-height: 1.5; margin: 8px 0; }
        .card-status {
            background: rgba(0, 0, 0, 0.35);
            border-radius: 12px;
            padding: 16px;
            margin: 15px 0;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .badge-online {
            background: #2e7d32;
            color: #fff;
            padding: 6px 14px;
            border-radius: 30px;
            font-weight: bold;
            display: inline-block;
            font-size: 13px;
        }
        .badge-waiting {
            background: #e65100;
            color: #fff;
            padding: 6px 14px;
            border-radius: 30px;
            font-weight: bold;
            display: inline-block;
            font-size: 13px;
        }
        .qr-box {
            background: #ffffff;
            padding: 15px;
            border-radius: 16px;
            display: inline-block;
            margin: 15px 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        .btn {
            background: #ff5722;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-top: 10px;
            transition: 0.2s;
        }
        .btn:hover { background: #e64a19; }
        .btn-pause { background: #d32f2f !important; }
        .btn-pause:hover { background: #b71c1c !important; }
        .btn-resume { background: #2e7d32 !important; }
        .btn-resume:hover { background: #1b5e20 !important; }
        .badge-ctrl {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            margin: 10px 0;
            transition: all 0.3s;
        }
        .stats-bar {
            display: flex;
            justify-content: space-around;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 10px;
            padding: 10px;
            margin: 15px 0;
            font-size: 12px;
            color: #b0bec5;
        }
        .stats-bar b { color: #fff; }
        .log-section {
            margin-top: 20px;
            text-align: left;
        }
        .log-header-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 15px;
            font-weight: bold;
            color: #ffb74d;
            margin-bottom: 10px;
        }
        .log-list {
            max-height: 320px;
            overflow-y: auto;
            background: rgba(0, 0, 0, 0.4);
            border-radius: 12px;
            padding: 10px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .log-item {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 8px;
            border-left: 4px solid #2196f3;
            font-size: 13px;
        }
        .log-item.cupom {
            border-left-color: #ff9800;
        }
        .log-row-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        .badge-tag {
            font-size: 10px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 10px;
        }
        .badge-cupom { background: #ff9800; color: #fff; }
        .badge-produto { background: #1976d2; color: #fff; }
        .log-time { color: #90a4ae; font-size: 11px; }
        .log-item-title {
            color: #f5f5f5;
            font-weight: 500;
            margin: 4px 0;
            word-break: break-word;
        }
        .log-row-bot {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 6px;
            font-size: 11px;
            color: #90a4ae;
        }
        .pill-status {
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(76, 175, 80, 0.2);
            color: #81c784;
            font-weight: 600;
            margin-left: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Achadinhos da Família 🛍️</h1>
        <p>Monitoramento e Automação Shopee em Nuvem 24/7</p>

        <div>
            <span id="badge-ctrl-envios" class="badge-ctrl" style="background: rgba(76, 175, 80, 0.2); color: #81c784; border: 1px solid #4caf50;">
                🟢 DISPAROS AUTOMÁTICOS ATIVOS
            </span>
        </div>

        <div id="status-card-box">
            <div class="card-status">
                <p>🔄 Verificando status dos serviços...</p>
            </div>
        </div>

        <div class="stats-bar">
            <span>📡 Radar: <b>5 Canais Ativos</b></span>
            <span>🕒 Última Checagem: <b id="stat-ultima">Ao vivo</b></span>
            <span>📦 Fila Reserva: <b id="stat-fila">58 prontas</b></span>
        </div>

        <div class="log-section">
            <div class="log-header-title">
                <span>📋 Feed de Envios em Tempo Real</span>
                <span id="contador-logs" style="font-size: 12px; color: #81c784; font-weight: normal;">Carregando...</span>
            </div>
            <div class="log-list" id="lista-logs">
                <div style="text-align: center; color: #90a4ae; padding: 20px;">Carregando histórico...</div>
            </div>
        </div>

        <div style="margin-top: 15px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button id="btn-toggle-envios" onclick="toggleEnvios()" class="btn btn-pause">⏸️ Pausar Envios</button>
            <a href="/varrer-agora" class="btn" style="background: #ff9800;">🚀 Forçar Disparo Agora</a>
            <button onclick="limparHistoricoLogs()" class="btn" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);">🗑️ Limpar Logs</button>
        </div>
    </div>

    <script>
        let enviosAtivos = true;

        async function limparHistoricoLogs() {
            if (confirm("Deseja realmente limpar o feed de logs antigos?")) {
                await fetch('/api/limpar-logs', { method: 'POST' });
                carregarLogs();
            }
        }

        async function toggleEnvios() {
            const btn = document.getElementById('btn-toggle-envios');
            btn.innerText = "⏳ Alterando...";
            btn.disabled = true;
            try {
                const res = await fetch('/api/toggle-envios', { method: 'POST' });
                const data = await res.json();
                atualizarBotaoEnvios(data.envios_ativos);
            } catch (e) {
                alert("Erro ao alterar status: " + e);
            } finally {
                btn.disabled = false;
            }
        }

        function atualizarBotaoEnvios(ativo) {
            enviosAtivos = ativo;
            const btn = document.getElementById('btn-toggle-envios');
            const badge = document.getElementById('badge-ctrl-envios');
            if (!btn || !badge) return;

            if (ativo) {
                btn.className = "btn btn-pause";
                btn.innerText = "⏸️ Pausar Envios";
                badge.style.background = "rgba(76, 175, 80, 0.2)";
                badge.style.color = "#81c784";
                badge.style.borderColor = "#4caf50";
                badge.innerText = "🟢 DISPAROS AUTOMÁTICOS ATIVOS";
            } else {
                btn.className = "btn btn-resume";
                btn.innerText = "▶️ Retomar Envios";
                badge.style.background = "rgba(244, 67, 54, 0.2)";
                badge.style.color = "#ff8a80";
                badge.style.borderColor = "#f44336";
                badge.innerText = "⏸️ ENVIOS PAUSADOS PELO USUÁRIO";
            }
        }

        async function checarRadar() {
            try {
                const res = await fetch('/api/status-radar');
                const data = await res.json();
                if (document.getElementById('stat-ultima')) {
                    document.getElementById('stat-ultima').innerText = data.ultima_varredura || 'Ao vivo';
                }
                if (document.getElementById('stat-fila')) {
                    document.getElementById('stat-fila').innerText = `${data.total_fila_reserva !== undefined ? data.total_fila_reserva : 0} prontas`;
                }
                if (data.envios_ativos !== undefined) {
                    atualizarBotaoEnvios(data.envios_ativos);
                }
            } catch (e) {}
        }

        async function checarStatus() {
            try {
                const res = await fetch('/whatsapp-status');
                const data = await res.json();
                const box = document.getElementById('status-card-box');
                const st = data.status_baileys || {};

                if (st.conectado) {
                    box.innerHTML = `
                        <div class="card-status">
                            <span class="badge-online">🟢 CONECTADO COM SUCESSO</span>
                            <h3 style="margin: 10px 0 4px 0; color: #a5d6a7; font-size: 16px;">Aparelho Ativo na Nuvem!</h3>
                            <p style="margin: 2px 0; font-size: 13px;">Dispositivo: <b>Achadinhos da Família</b></p>
                            <p style="margin: 2px 0; font-size: 13px;">Grupo Alvo: <b>${st.jidGrupo || 'Achadiinhos da Família'}</b></p>
                        </div>
                    `;
                } else if (st.qr) {
                    const qrUrl = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=" + encodeURIComponent(st.qr);
                    box.innerHTML = `
                        <div class="card-status">
                            <span class="badge-waiting">📲 LEIA O QR CODE</span>
                            <div class="qr-box">
                                <img src="${qrUrl}" alt="QR Code WhatsApp" width="240" height="240" />
                            </div>
                            <p style="font-size: 13px; color: #ffb74d;">Abra o WhatsApp > Aparelhos Conectados > Conectar um Aparelho</p>
                        </div>
                    `;
                } else {
                    box.innerHTML = `
                        <div class="card-status">
                            <p>⏳ O conector Baileys está iniciando ou gerando o QR Code...</p>
                        </div>
                    `;
                }
            } catch (err) {
                console.error(err);
            }
        }

        async function carregarLogs() {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                const lista = document.getElementById('lista-logs');
                const contador = document.getElementById('contador-logs');

                if (contador) {
                    contador.innerText = `${data.total || 0} envios registrados`;
                }

                if (!data.logs || data.logs.length === 0) {
                    lista.innerHTML = '<div style="text-align: center; color: #90a4ae; padding: 25px;">Nenhum envio recente ainda. Aguardando novo ciclo da varredura...</div>';
                    return;
                }

                lista.innerHTML = data.logs.map(item => `
                    <div class="log-item ${item.tipo === 'CUPOM' ? 'cupom' : 'produto'}">
                        <div class="log-row-top">
                            <span class="badge-tag ${item.tipo === 'CUPOM' ? 'badge-cupom' : 'badge-produto'}">
                                ${item.tipo === 'CUPOM' ? '🎟️ CUPOM' : '🛍️ OFERTA'}
                            </span>
                            <span class="log-time">🕒 ${item.hora}</span>
                        </div>
                        <div class="log-item-title">
                            <a href="${item.link}" target="_blank" style="color: #fff; text-decoration: none;">${item.titulo}</a>
                        </div>
                        <div class="log-row-bot">
                            <span>Origem: <b>${item.canal}</b></span>
                            <span>
                                <span class="pill-status">🟢 WPP: ${item.wpp}</span>
                                <span class="pill-status" style="background: rgba(33, 150, 243, 0.2); color: #90caf9;">🔵 TG: ${item.tg}</span>
                            </span>
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                console.error("Erro ao puxar logs:", e);
            }
        }

        checarStatus();
        checarRadar();
        carregarLogs();
        setInterval(checarStatus, 4000);
        setInterval(checarRadar, 4000);
        setInterval(carregarLogs, 4000);
    </script>
</body>
</html>
"""

@app.route("/whatsapp")
@app.route("/")
def rota_whatsapp():
    return render_template_string(HTML_WHATSAPP)

@app.route("/ping")
@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "app": "Achadinhos da Família",
        "servico": "Radar de Ofertas e Cupons Shopee 24/7",
        "canais_monitorados": 5,
        "timestamp": int(time.time())
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
