import os
import sys
import csv
import re
import time
import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram

CSV_PATH = r"C:\Users\TRANSRAP05\Downloads\BatchProductLinks20260930090819-a3e7fa514b494740b14286a9caf19920.csv"
PASTA_MIDIA = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\midia"
PASTA_STORIES = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\stories_instagram"

os.makedirs(PASTA_MIDIA, exist_ok=True)
os.makedirs(PASTA_STORIES, exist_ok=True)

def processar_lote_csv():
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = list(csv.DictReader(f))

    print(f"Total de produtos para processar: {len(reader)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, # Visível para não disparar anti-crawler
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for idx, row in enumerate(reader, 1):
            item_id = row.get("Item Id")
            nome_original = row.get("Item Name", "Produto Shopee")
            preco = row.get("Price", "0,00").replace(".", ",")
            link_afiliado = row.get("Offer Link")
            link_produto = row.get("Product Link")

            print(f"\n[{idx}/{len(reader)}] Processando: {nome_original[:35]}... (R$ {preco})")

            # 1. Encurta título para ficar bonito e limpo no card
            palavras = nome_original.split()
            titulo_limpo = " ".join(palavras[:6])

            # 2. Obter imagem do produto
            caminho_foto = os.path.join(PASTA_MIDIA, f"item_{item_id}.jpg")
            img_url = None

            try:
                page.goto(link_produto, timeout=25000)
                time.sleep(2)
                # Tenta pegar og:image
                elem = page.query_selector('meta[property="og:image"]')
                if elem:
                    img_url = elem.get_attribute("content")
                if not img_url:
                    # Tenta imagem principal do carrossel
                    img_elem = page.query_selector('img[src*="susercontent.com"]')
                    if img_elem:
                        img_url = img_elem.get_attribute("src")
            except Exception as e:
                print(f"Erro ao carregar página: {e}")

            if img_url:
                try:
                    r = requests.get(img_url, timeout=15)
                    with open(caminho_foto, "wb") as f_img:
                        f_img.write(r.content)
                except Exception as e:
                    print(f"Erro ao baixar imagem: {e}")

            # 3. Gerar Story 9:16
            caminho_story = os.path.join(PASTA_STORIES, f"story_{item_id}.png")
            preco_float = float(preco.replace(",", "."))
            preco_antigo = f"{preco_float * 1.5:.2f}".replace(".", ",") # Estimativa do valor riscado "De"

            criar_story_9_16(
                caminho_foto_produto=caminho_foto,
                titulo=titulo_limpo,
                preco=preco,
                preco_antigo=preco_antigo,
                cupom="Selecione o cupom de frete no carrinho",
                caminho_saida=caminho_story
            )
            print(f"Story gerado em: {caminho_story}")

            # 4. Enviar para o Telegram
            legenda_tg = f"🛍️ <b>{titulo_limpo}</b>\n\n💰 <b>Por apenas: R$ {preco}</b>\n🚚 <b>Frete:</b> Ative o cupom no carrinho\n\n🔗 <b>Link de Afiliado (Toque e Copie):</b>\n{link_afiliado}"
            res_tg = enviar_para_telegram(caminho_story, legenda_tg)
            print(f"Envio Telegram: {res_tg.get('sucesso')} | {res_tg.get('mensagem', res_tg.get('erro'))}")

            time.sleep(2)

        browser.close()
    print("\nProcessamento do lote finalizado com sucesso!")

if __name__ == "__main__":
    processar_lote_csv()
