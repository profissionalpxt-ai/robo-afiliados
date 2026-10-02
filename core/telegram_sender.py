import os
import json
import requests

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "configuracoes.json"))

def enviar_para_telegram(caminho_foto: str, texto_legenda: str) -> dict:
    """
    Envia a foto do produto/story diretamente para o Telegram do usuário
    com o link pronto para copiar.
    """
    if not os.path.exists(CONFIG_PATH):
        return {"sucesso": False, "erro": "Arquivo de configurações não encontrado"}
        
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    token = cfg.get("telegram_token")
    chat_id = cfg.get("telegram_chat_id")
    
    if not token or not chat_id:
        return {"sucesso": False, "erro": "Telegram não configurado (token ou chat_id ausente)"}
        
    if not os.path.exists(caminho_foto):
        return {"sucesso": False, "erro": f"Arquivo não encontrado: {caminho_foto}"}
        
    url_api = f"https://api.telegram.org/bot{token}/sendPhoto"
    
    try:
        with open(caminho_foto, "rb") as foto:
            payload = {
                "chat_id": chat_id,
                "caption": texto_legenda,
                "parse_mode": "HTML"
            }
            files = {"photo": foto}
            r = requests.post(url_api, data=payload, files=files, timeout=30)
            res = r.json()
            if res.get("ok"):
                return {"sucesso": True, "mensagem": "Enviado com sucesso!"}
            else:
                return {"sucesso": False, "erro": res.get("description")}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

def enviar_video_telegram(caminho_video: str, texto_legenda: str) -> dict:
    """
    Envia um arquivo de vídeo (.mp4) diretamente para o Telegram do usuário.
    """
    if not os.path.exists(CONFIG_PATH):
        return {"sucesso": False, "erro": "Arquivo de configurações não encontrado"}
        
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        
    token = cfg.get("telegram_token")
    chat_id = cfg.get("telegram_chat_id")
    
    if not token or not chat_id:
        return {"sucesso": False, "erro": "Telegram não configurado"}
        
    if not os.path.exists(caminho_video):
        return {"sucesso": False, "erro": f"Arquivo não encontrado: {caminho_video}"}
        
    url_api = f"https://api.telegram.org/bot{token}/sendVideo"
    
    try:
        with open(caminho_video, "rb") as video:
            payload = {
                "chat_id": chat_id,
                "caption": texto_legenda,
                "parse_mode": "HTML"
            }
            files = {"video": video}
            r = requests.post(url_api, data=payload, files=files, timeout=60)
            res = r.json()
            if res.get("ok"):
                return {"sucesso": True, "mensagem": "Vídeo enviado com sucesso!"}
            else:
                return {"sucesso": False, "erro": res.get("description")}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

