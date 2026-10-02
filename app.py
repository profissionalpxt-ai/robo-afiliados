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

@app.route("/")
def index():
    return render_template_string(HTML_DASHBOARD)

import gc
import subprocess

def iniciar_servico_baileys():
    time.sleep(2)
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
    # Aguarda 15 segundos para dar tempo do Baileys subir e conectar
    time.sleep(15)
    while True:
        try:
            from core.radar_shopee import varrer_canais
            varrer_canais()
        except Exception as e:
            print(f"Erro no loop do radar: {e}")
        gc.collect()
        time.sleep(180)

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
