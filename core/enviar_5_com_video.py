import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import requests
import json
from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram

CONFIG_PATH = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\config\configuracoes.json"
PASTA_MIDIA = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\midia"
PASTA_STORIES = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\stories_instagram"
PASTA_VIDEOS = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\videos_instagram"

def enviar_video_telegram(caminho_video: str, legenda: str):
    cfg = json.load(open(CONFIG_PATH, "r", encoding="utf-8"))
    token = cfg.get("telegram_token")
    chat_id = cfg.get("telegram_chat_id")
    url_api = f"https://api.telegram.org/bot{token}/sendVideo"
    try:
        with open(caminho_video, "rb") as video:
            r = requests.post(
                url_api, 
                data={"chat_id": chat_id, "caption": legenda, "parse_mode": "HTML"}, 
                files={"video": video}, 
                timeout=60
            )
            return r.json()
    except Exception as e:
        return {"ok": False, "erro": str(e)}

produtos = [
    {
        "id": "21897981294",
        "titulo": "Perfume Attracione Men Feromônios Ativados",
        "preco": "29,90",
        "preco_antigo": "59,90",
        "img_url": "https://down-br.img.susercontent.com/file/sg-11134201-7repr-m2v3wdwedwcb1f",
        "link": "https://s.shopee.com.br/8AWV5yqgQl",
        "cupom": "Selecione o cupom de frete no carrinho"
    },
    {
        "id": "18698093887",
        "titulo": "Kit Noite Perfeita Cetim Touca Fronha Xuxinha",
        "preco": "14,90",
        "preco_antigo": "29,90",
        "img_file": "item_18698093887.jpg",
        "link": "https://s.shopee.com.br/9V1sgSKKfc",
        "cupom": "Selecione o cupom de frete no carrinho"
    },
    {
        "id": "23199657010",
        "titulo": "Kit Puro Leite Completo Cap Life Corporal",
        "preco": "19,90",
        "preco_antigo": "32,90",
        "img_url": "https://down-br.img.susercontent.com/file/br-11134207-820lq-mrs5pty9st8l90",
        "link": "https://s.shopee.com.br/4B0MKjPPwl",
        "cupom": "Selecione o cupom de frete no carrinho"
    },
    {
        "id": "27142661681",
        "titulo": "Kit Protetor Solar Nivea Sun Adulto e Infantil",
        "preco": "49,90",
        "preco_antigo": "89,90",
        "img_file": "item_27142661681.jpg",
        "link": "https://s.shopee.com.br/905c5ejsJx",
        "cupom": "Selecione o cupom de frete no carrinho"
    },
    {
        "id": "11913057310",
        "titulo": "Prancha Chapinha Taiff Cerâmica 180C Bivolt",
        "preco": "109,90",
        "preco_antigo": "159,90",
        "img_file": "item_11913057310.jpg",
        "link": "https://s.shopee.com.br/70KXi0LoZH",
        "cupom": "Selecione o cupom de frete no carrinho",
        "video": os.path.join(PASTA_VIDEOS, "video_taiff.mp4")
    }
]

print("Iniciando geração das 5 artes e disparo...")

for idx, p in enumerate(produtos, 1):
    caminho_foto = os.path.join(PASTA_MIDIA, f"item_{p['id']}.jpg")
    if p.get("img_url"):
        try:
            r = requests.get(p["img_url"], timeout=15)
            with open(caminho_foto, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print("Erro ao baixar foto:", e)

    caminho_story = os.path.join(PASTA_STORIES, f"story_{p['id']}.png")
    criar_story_9_16(
        caminho_foto_produto=caminho_foto,
        titulo=p["titulo"],
        preco=p["preco"],
        preco_antigo=p["preco_antigo"],
        cupom=p["cupom"],
        caminho_saida=caminho_story
    )
    print(f"[{idx}/5] Story gerado: {p['titulo']}")

    legenda = f"🛍️ <b>{p['titulo']}</b>\n\n💰 <b>Por apenas: R$ {p['preco']}</b> (De R$ {p['preco_antigo']})\n🚚 <b>Frete:</b> Ative o cupom no carrinho\n\n🔗 <b>Link de Afiliado (Toque e Copie):</b>\n{p['link']}"
    res = enviar_para_telegram(caminho_story, legenda)
    print(f"Envio Telegram: {res}")
    time.sleep(2)

# Disparo do Vídeo de Demonstração
vid_path = os.path.join(PASTA_VIDEOS, "video_taiff.mp4")
if os.path.exists(vid_path):
    print("Disparando vídeo de demonstração no Telegram...")
    legenda_vid = "🎬 <b>VÍDEO DE DEMONSTRAÇÃO (REELS / STORIES)</b>\n\n👉 <b>Prancha Chapinha Taiff Cerâmica Bivolt</b>\n💰 <b>R$ 109,90</b>\n\n🔗 <b>Link para colocar na figurinha:</b>\nhttps://s.shopee.com.br/70KXi0LoZH"
    res_vid = enviar_video_telegram(vid_path, legenda_vid)
    print("Envio Vídeo Telegram:", res_vid)

print("Finalizado com sucesso!")
