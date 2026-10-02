import requests
import os
import json

URL_BAILEYS = "http://127.0.0.1:3333"

def verificar_conexao_baileys() -> dict:
    """Verifica se o conector Baileys está ativo e conectado ao WhatsApp"""
    try:
        r = requests.get(f"{URL_BAILEYS}/status", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"conectado": False, "erro": "Conector Baileys não está rodando na porta 3333"}

def enviar_para_grupo_whatsapp(caminho_foto: str, texto_legenda: str, grupo_jid: str = None) -> dict:
    """Envia uma oferta formatada com foto diretamente para o grupo do WhatsApp via Baileys"""
    try:
        payload = {
            "foto": os.path.abspath(caminho_foto) if caminho_foto and os.path.exists(caminho_foto) else "",
            "legenda": texto_legenda
        }
        if grupo_jid:
            payload["grupo"] = grupo_jid

        r = requests.post(f"{URL_BAILEYS}/enviar", json=payload, timeout=20)
        return r.json()
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

if __name__ == "__main__":
    status = verificar_conexao_baileys()
    print("Status do WhatsApp Baileys:", status)
