import os
import sys
import re
import time
import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "configuracoes.json")
PASTA_MIDIA = os.path.join(os.path.dirname(__file__), "..", "midia")
PASTA_STORIES = os.path.join(os.path.dirname(__file__), "..", "stories_instagram")
PASTA_VIDEOS = os.path.join(os.path.dirname(__file__), "..", "videos_instagram")

os.makedirs(PASTA_MIDIA, exist_ok=True)
os.makedirs(PASTA_STORIES, exist_ok=True)
os.makedirs(PASTA_VIDEOS, exist_ok=True)

PRODUTOS = [
    {"url_curta": "https://s.shopee.com.br/8AWV5yqgQl", "shopid": "1266325318", "itemid": "21897981294"},
    {"url_curta": "https://s.shopee.com.br/9V1sgSKKfc", "shopid": "718725893", "itemid": "18698093887"},
    {"url_curta": "https://s.shopee.com.br/4B0MKjPPwl", "shopid": "352072066", "itemid": "23199657010"},
    {"url_curta": "https://s.shopee.com.br/905c5ejsJx", "shopid": "1263405995", "itemid": "27142661681"},
    {"url_curta": "https://s.shopee.com.br/70KXi0LoZH", "shopid": "418231105", "itemid": "11913057310"},
]

def enviar_video_telegram(caminho_video: str, legenda: str):
    import json
    cfg = json.load(open(CONFIG_PATH, "r", encoding="utf-8"))
    token = cfg.get("telegram_token")
    chat_id = cfg.get("telegram_chat_id")
    url_api = f"https://api.telegram.org/bot{token}/sendVideo"
    try:
        with open(caminho_video, "rb") as video:
            r = requests.post(url_api, data={"chat_id": chat_id, "caption": legenda, "parse_mode": "HTML"}, files={"video": video}, timeout=60)
            return r.json()
    except Exception as e:
        return {"ok": False, "erro": str(e)}

def executar():
    print("Iniciando varredura com Playwright para os 5 produtos...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        video_encontrado = None

        for idx, prod in enumerate(PRODUTOS, 1):
            url_pdp = f"https://shopee.com.br/product/{prod['shopid']}/{prod['itemid']}"
            itemid = prod['itemid']
            link_afiliado = prod['url_curta']
            
            print(f"\n--- [{idx}/5] Acessando Item {itemid} ---")
            
            try:
                page.goto(url_pdp, timeout=30000)
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"Erro no carregamento: {e}")

            # 1. Título
            titulo = ""
            meta_tit = page.query_selector('meta[property="og:title"]')
            if meta_tit:
                titulo = meta_tit.get_attribute("content") or ""
                titulo = titulo.replace(" | Shopee Brasil", "").strip()
            if not titulo:
                elem_h1 = page.query_selector('h1, span[class*="product-title"]')
                if elem_h1:
                    titulo = elem_h1.inner_text().strip()
            if not titulo:
                titulo = "Produto Shopee em Oferta"
                
            print(f"Título: {titulo}")

            # 2. Imagem
            img_url = ""
            meta_img = page.query_selector('meta[property="og:image"]')
            if meta_img:
                img_url = meta_img.get_attribute("content") or ""
            if not img_url:
                for im in page.query_selector_all('img'):
                    src = im.get_attribute('src') or ''
                    if 'susercontent.com/file/' in src:
                        img_url = src
                        break

            caminho_img = os.path.join(PASTA_MIDIA, f"item_{itemid}.jpg")
            if img_url:
                try:
                    r = requests.get(img_url, timeout=15)
                    with open(caminho_img, "wb") as f:
                        f.write(r.content)
                    print(f"Foto salva em: {caminho_img}")
                except Exception as e:
                    print(f"Erro download foto: {e}")

            # 3. Preço
            preco = ""
            # Procura por elementos de preço na página
            for sel in ['div[class*="price"]', 'div[class*="Price"]', 'span[class*="price"]', 'span[class*="Price"]']:
                for el in page.query_selector_all(sel):
                    txt = el.inner_text()
                    m = re.search(r'R\$\s*([0-9]{1,4}[,\.][0-9]{2})', txt)
                    if m:
                        preco = m.group(1).replace(".", ",")
                        break
                if preco:
                    break

            if not preco:
                preco = "Consulte no App"

            print(f"Preço identificado: R$ {preco}")

            # 4. Checar se tem vídeo
            if not video_encontrado:
                try:
                    v_elem = page.query_selector('video')
                    if v_elem:
                        v_src = v_elem.get_attribute('src')
                        if v_src and v_src.startswith('http'):
                            caminho_vid = os.path.join(PASTA_VIDEOS, f"video_{itemid}.mp4")
                            rv = requests.get(v_src, timeout=30)
                            with open(caminho_vid, "wb") as fv:
                                fv.write(rv.content)
                            video_encontrado = {
                                "caminho": caminho_vid,
                                "titulo": titulo,
                                "link": link_afiliado
                            }
                            print(f"🎬 VÍDEO DO PRODUTO ENCONTRADO E BAIXADO: {caminho_vid}")
                except Exception as e:
                    print(f"Erro ao capturar vídeo: {e}")

            # 5. Gerar Story 9:16
            caminho_story = os.path.join(PASTA_STORIES, f"story_{itemid}.png")
            # Encurta título para ficar agradável no card
            titulo_card = " ".join(titulo.split()[:7])
            
            # Estimativa de preço riscado se tiver preço numérico
            preco_antigo = ""
            try:
                p_num = float(preco.replace(",", "."))
                preco_antigo = f"{p_num * 1.45:.2f}".replace(".", ",")
            except Exception:
                preco_antigo = ""

            criar_story_9_16(
                caminho_foto_produto=caminho_img,
                titulo=titulo_card,
                preco=preco,
                preco_antigo=preco_antigo,
                cupom="Selecione o cupom de frete no carrinho",
                caminho_saida=caminho_story
            )
            print(f"Story gerado em: {caminho_story}")

            # 6. Disparar no Telegram
            legenda_tg = f"🛍️ <b>{titulo_card}</b>\n\n💰 <b>Por apenas: R$ {preco}</b>\n🚚 <b>Frete:</b> Ative o cupom de frete no carrinho\n\n🔗 <b>Link de Afiliado (Toque e Copie):</b>\n{link_afiliado}"
            res = enviar_para_telegram(caminho_story, legenda_tg)
            print(f"Envio Telegram: {res}")
            time.sleep(2)

        # Se encontrou vídeo, dispara o vídeo também!
        if video_encontrado:
            print("\nEnviando o vídeo de demonstração para o Telegram...")
            legenda_vid = f"🎬 <b>VÍDEO DE DEMONSTRAÇÃO (REELS/STORIES)</b>\n\n👉 <b>{video_encontrado['titulo']}</b>\n\n🔗 <b>Link para colocar na figurinha:</b>\n{video_encontrado['link']}"
            res_v = enviar_video_telegram(video_encontrado['caminho'], legenda_vid)
            print(f"Envio Vídeo Telegram: {res_v}")

        browser.close()
    print("\nTODOS OS 5 PRODUTOS PROCESSADOS COM SUCESSO!")

if __name__ == "__main__":
    executar()
