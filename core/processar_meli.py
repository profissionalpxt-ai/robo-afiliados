import os
import sys
import re
import json
import time
import requests
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram

PASTA_MIDIA = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\midia"
PASTA_STORIES = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\stories_instagram"
CAMINHO_FILA = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\fila\ofertas_prontas.json"

links_meli = [
    'https://meli.la/12YPTw3',
    'https://meli.la/1jg6qRW',
    'https://meli.la/2vX25Yn',
    'https://meli.la/1F5Vhii',
    'https://meli.la/34d3Lek'
]

headers = {
    'User-Agent': 'MercadoLibre/10.0 (Android; 13; SM-G998B)',
    'x-platform': 'android'
}

print(f"Processando {len(links_meli)} produtos do Mercado Livre...")

fila = []
if os.path.exists(CAMINHO_FILA):
    try:
        fila = json.load(open(CAMINHO_FILA, "r", encoding="utf-8"))
    except Exception:
        pass

for idx, link in enumerate(links_meli, 1):
    print(f"\n[{idx}/5] Acessando {link}...")
    try:
        r = requests.get(link, headers=headers, timeout=20)
        m = re.search(r'_n\.ctx\.r=({.*?});', r.text)
        if not m:
            print(f"Dados não encontrados para {link}")
            continue

        data = json.loads(m.group(1))
        comps = data.get('appProps', {}).get('pageProps', {}).get('data', {}).get('components', [])
        
        poly = None
        for c in comps:
            if c.get('id') == 'card-featured':
                polys = c.get('recommendation_data', {}).get('recommendation_info', {}).get('polycards', [])
                if polys:
                    poly = polys[0]
                    break

        if not poly:
            print(f"Nenhum polycard encontrado para {link}")
            continue

        # Extrair título, preço anterior e preço atual
        titulo = "Produto Mercado Livre"
        preco_atual = "0,00"
        preco_anterior = ""
        cupom_info = "Frete Grátis pelo FULL"

        for comp in poly.get('components', []):
            c_type = comp.get('type')
            if c_type == 'title':
                titulo = comp.get('title', {}).get('text', titulo)
            elif c_type == 'price':
                p_info = comp.get('price', {})
                curr_val = p_info.get('current_price', {}).get('value')
                prev_val = p_info.get('previous_price', {}).get('value')
                if curr_val:
                    preco_atual = f"{curr_val:.2f}".replace(".", ",")
                if prev_val:
                    preco_anterior = f"{prev_val:.2f}".replace(".", ",")
            elif c_type == 'promotions':
                promos = comp.get('promotions', [])
                if promos:
                    p_txt = promos[0].get('text', '')
                    p_vals = promos[0].get('values', [])
                    if p_vals and 'price' in p_vals[0]:
                        c_val = p_vals[0]['price'].get('value')
                        cupom_info = f"R$ {c_val:.2f} com Cupom no App".replace(".", ",")
                    elif p_txt:
                        cupom_info = p_txt

        # Imagem
        img_url = ""
        pics = poly.get('pictures', {}).get('pictures', [])
        if pics:
            pic_id = pics[0].get('id')
            img_url = f"https://http2.mlstatic.com/D_NQ_NP_{pic_id}-O.webp"

        caminho_foto = os.path.join(PASTA_MIDIA, f"meli_{idx}.webp")
        if img_url:
            r_img = requests.get(img_url, timeout=15)
            with open(caminho_foto, "wb") as f_i:
                f_i.write(r_img.content)

        # Encurtar título
        palavras = titulo.split()
        titulo_card = " ".join(palavras[:7])

        # Gerar Story 9:16
        caminho_story = os.path.join(PASTA_STORIES, f"story_meli_{idx}.png")
        criar_story_9_16(
            caminho_foto_produto=caminho_foto,
            titulo=titulo_card,
            preco=preco_atual,
            preco_antigo=preco_anterior,
            cupom=cupom_info,
            caminho_saida=caminho_story
        )
        print(f"Story criado: {titulo_card} (R$ {preco_atual})")

        # Disparar no Telegram
        legenda = f"📦 <b>{titulo_card}</b>\n\n💰 <b>Por apenas: R$ {preco_atual}</b>"
        if preco_anterior:
            legenda += f" (De R$ {preco_anterior})"
        legenda += f"\n🚚 <b>Benefício:</b> {cupom_info}\n\n🔗 <b>Link de Afiliado (Toque e Copie):</b>\n{link}"
        
        res_tg = enviar_para_telegram(caminho_story, legenda)
        print(f"Envio Telegram: {res_tg}")

        # Adicionar na fila do WhatsApp
        fila.append({
            "titulo": titulo_card,
            "preco": preco_atual,
            "preco_antigo": preco_anterior,
            "condicao": cupom_info,
            "link_afiliado": link,
            "caminho_imagem": caminho_foto,
            "caminho_story": caminho_story
        })

        time.sleep(2)

    except Exception as e:
        print(f"Erro ao processar {link}: {e}")

with open(CAMINHO_FILA, "w", encoding="utf-8") as f:
    json.dump(fila, f, indent=2, ensure_ascii=False)

print("\nProcessamento Mercado Livre finalizado com sucesso!")
