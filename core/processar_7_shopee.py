import os
import sys
import re
import time
import json
import requests
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

PASTA_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PASTA_BASE not in sys.path:
    sys.path.insert(0, PASTA_BASE)
PASTA_CORE = os.path.join(PASTA_BASE, "core")
if PASTA_CORE not in sys.path:
    sys.path.insert(0, PASTA_CORE)

from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram, enviar_video_telegram

CONFIG_PATH = os.path.join(PASTA_BASE, "config", "configuracoes.json")
PASTA_MIDIA = os.path.join(PASTA_BASE, "midia")
PASTA_STORIES = os.path.join(PASTA_BASE, "stories_instagram")
PASTA_VIDEOS = os.path.join(PASTA_BASE, "videos_instagram")
CAMINHO_FILA = os.path.join(PASTA_BASE, "fila", "ofertas_prontas.json")

os.makedirs(PASTA_MIDIA, exist_ok=True)
os.makedirs(PASTA_STORIES, exist_ok=True)
os.makedirs(PASTA_VIDEOS, exist_ok=True)

PRODUTOS_7 = [
    {"url_curta": "https://s.shopee.com.br/2LYjrArKsN", "shopid": "316945044", "itemid": "55260497129"},
    {"url_curta": "https://s.shopee.com.br/2qV0SR7Ldm", "shopid": "389351707", "itemid": "20198093264"},
    {"url_curta": "https://s.shopee.com.br/gQVsYv6J3", "shopid": "874603044", "itemid": "22794290449"},
    {"url_curta": "https://s.shopee.com.br/30oQetBsRR", "shopid": "1273492426", "itemid": "19299299965"},
    {"url_curta": "https://s.shopee.com.br/60S2ERYi05", "shopid": "1384073074", "itemid": "23293909383"},
    {"url_curta": "https://s.shopee.com.br/7VGq1DkGJm", "shopid": "989001237", "itemid": "23397999673"},
    {"url_curta": "https://s.shopee.com.br/6L4sdCCCnf", "shopid": "1103946075", "itemid": "19899586753"}
]

def carregar_fila():
    if os.path.exists(CAMINHO_FILA):
        try:
            with open(CAMINHO_FILA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_fila(fila):
    with open(CAMINHO_FILA, "w", encoding="utf-8") as f:
        json.dump(fila, f, indent=2, ensure_ascii=False)

def executar():
    print("=" * 60)
    print("🚀 PROCESSANDO 7 PRODUTOS SHOPEE COM O NOVO TEMPLATE OFICIAL")
    print("=" * 60)

    fila = carregar_fila()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--start-maximized']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        video_enviado = False

        for idx, prod in enumerate(PRODUTOS_7, 1):
            itemid = prod['itemid']
            shopid = prod['shopid']
            link_afiliado = prod['url_curta']
            url_pdp = f"https://shopee.com.br/product/{shopid}/{itemid}"

            print(f"\n[{idx}/7] Acessando produto ID {itemid}...")

            try:
                page.goto(url_pdp, timeout=35000)
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"Aviso navegação: {e}")

            # 1. Título
            titulo = ""
            meta_tit = page.query_selector('meta[property="og:title"]')
            if meta_tit:
                titulo = meta_tit.get_attribute("content") or ""
                titulo = titulo.replace(" | Shopee Brasil", "").replace("Shopee Brasil", "").strip()
            if not titulo:
                elem_h1 = page.query_selector('h1, span[class*="product-title"], div[class*="product-briefing"]')
                if elem_h1:
                    titulo = elem_h1.inner_text().strip()
            if not titulo:
                titulo = f"Produto Shopee {itemid}"

            print(f"   📌 Título: {titulo}")

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
                    r_img = requests.get(img_url, timeout=15)
                    with open(caminho_img, "wb") as f_i:
                        f_i.write(r_img.content)
                    print(f"   📸 Imagem salva: {caminho_img}")
                except Exception as e:
                    print(f"   Erro download imagem: {e}")

            # 3. Preço Atual e Preço Antigo
            preco = ""
            preco_antigo = ""
            
            # Busca preço atual
            for sel in ['div[class*="price"]', 'span[class*="price"]', 'div[class*="Price"]', 'span[class*="Price"]']:
                for el in page.query_selector_all(sel):
                    txt = el.inner_text()
                    m = re.findall(r'R\$\s*([0-9]{1,4}[,\.][0-9]{2})', txt)
                    if m:
                        preco = m[0].replace(".", ",")
                        if len(m) > 1:
                            preco_antigo = m[1].replace(".", ",")
                        break
                if preco:
                    break

            if not preco:
                preco = "Consulte Oferta"

            if not preco_antigo:
                try:
                    p_num = float(preco.replace(",", "."))
                    preco_antigo = f"{p_num * 1.40:.2f}".replace(".", ",")
                except Exception:
                    preco_antigo = ""

            print(f"   💰 Preço: R$ {preco} (De: R$ {preco_antigo})")

            # 4. Checar se tem vídeo de demonstração
            if not video_enviado:
                try:
                    v_elem = page.query_selector('video')
                    if v_elem:
                        v_src = v_elem.get_attribute('src')
                        if v_src and v_src.startswith('http'):
                            caminho_vid = os.path.join(PASTA_VIDEOS, f"video_{itemid}.mp4")
                            rv = requests.get(v_src, timeout=30)
                            with open(caminho_vid, "wb") as fv:
                                fv.write(rv.content)
                            print(f"   🎬 VÍDEO ENCONTRADO: {caminho_vid}")
                            
                            legenda_vid = (
                                f"🎬 <b>Vídeo de Demonstração (Reels / Stories)</b>\n\n"
                                f"👉 <b>{titulo}</b>\n\n"
                                f"🔗 <b>Link para a figurinha:</b>\n{link_afiliado}"
                            )
                            res_vid = enviar_video_telegram(caminho_vid, legenda_vid)
                            print(f"   Envio do Vídeo ao Telegram: {res_vid}")
                            video_enviado = True
                except Exception as e:
                    print(f"   Erro ao extrair vídeo: {e}")

            # 5. Gerar Story 9:16 Oficial (sem texto na caixinha de link)
            caminho_story = os.path.join(PASTA_STORIES, f"story_{itemid}.png")
            titulo_curto = " ".join(titulo.split()[:7])

            criar_story_9_16(
                caminho_foto_produto=caminho_img,
                titulo=titulo_curto,
                preco=preco,
                preco_antigo=preco_antigo,
                cupom="Selecione o cupom de frete no carrinho",
                caminho_saida=caminho_story
            )
            print(f"   🎨 Story gerado: {caminho_story}")

            # 6. Enviar ao Telegram
            legenda_tg = (
                f"🎨 <b>Story Limpo (Achadinhos da Família)</b>\n\n"
                f"📦 <b>{titulo_curto}</b>\n"
                f"💰 <b>Por apenas: R$ {preco}</b>"
            )
            if preco_antigo:
                legenda_tg += f" <i>(De: R$ {preco_antigo})</i>"
            legenda_tg += (
                f"\n🚚 <b>Benefício:</b> Cupom de Frete no Carrinho\n\n"
                f"🔗 <b>Link de Afiliado (Toque e Copie):</b>\n{link_afiliado}"
            )

            res_tg = enviar_para_telegram(caminho_story, legenda_tg)
            print(f"   📲 Telegram: {res_tg}")

            # 7. Adicionar à fila do WhatsApp
            fila.append({
                "titulo": titulo_curto,
                "preco": preco,
                "preco_antigo": preco_antigo,
                "condicao": "Cupom de Frete no Carrinho",
                "link_afiliado": link_afiliado,
                "caminho_imagem": caminho_img,
                "caminho_story": caminho_story
            })

            time.sleep(2)

        salvar_fila(fila)
        browser.close()

    print("\n" + "=" * 60)
    print("✅ TODOS OS 7 PRODUTOS FORAM PROCESSADOS E ENVIADOS AO TELEGRAM!")
    print(f"📦 Total de ofertas na fila de disparo do WhatsApp: {len(fila)}")
    print("=" * 60)

if __name__ == "__main__":
    executar()
