import os
import sys
import csv
import json
import time
import re
import requests
from PIL import Image

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram
from playwright.sync_api import sync_playwright

PASTA_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA_MIDIA = os.path.join(PASTA_BASE, "midia")
PASTA_STORIES = os.path.join(PASTA_BASE, "stories_instagram")
CAMINHO_FILA = os.path.join(PASTA_BASE, "fila", "ofertas_prontas.json")
CSV_PATH = os.path.join(PASTA_BASE, "input_planilhas", "BatchProductLinks20261002091427-c4dfb19f77c248a691933d68c5517e1d.csv")

os.makedirs(PASTA_MIDIA, exist_ok=True)
os.makedirs(PASTA_STORIES, exist_ok=True)

def carregar_planilha():
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def baixar_imagem_produto(page, url_produto, url_afiliado, item_id):
    caminho_foto = os.path.join(PASTA_MIDIA, f"prod_{item_id}.jpg")
    
    # Se já existir e for válida (> 10KB), reaproveita
    if os.path.exists(caminho_foto) and os.path.getsize(caminho_foto) > 10000:
        try:
            with Image.open(caminho_foto) as img:
                img.verify()
            print(f"   ✅ Foto já existe em cache: {caminho_foto}")
            return caminho_foto
        except Exception:
            pass

    for tentativa_url in [url_produto, url_afiliado]:
        print(f"   🌐 Acessando página ({tentativa_url[:60]}...)...")
        try:
            page.goto(tentativa_url, timeout=35000)
            page.wait_for_timeout(4000)
        except Exception as e:
            print(f"   ⚠️ Erro ao carregar página: {e}")
            continue

        # 1. Tenta pegar og:image
        img_url = ""
        try:
            el_og = page.locator('meta[property="og:image"]').first
            if el_og.count() > 0:
                img_url = el_og.get_attribute("content") or ""
        except Exception:
            pass
            
        # 2. Tenta pegar de tags <img> do DOM
        if not img_url or "susercontent.com" not in img_url:
            try:
                for selector in ['img[src*="susercontent.com/file/"]', 'img[src*="down-br.img.susercontent.com"]']:
                    locs = page.locator(selector).all()
                    for loc in locs:
                        src = loc.get_attribute("src") or ""
                        if "susercontent.com/file/" in src and "avatar" not in src and "shop" not in src:
                            img_url = src.split('_tn')[0].split('_sq')[0]
                            break
                    if img_url:
                        break
            except Exception:
                pass

        # 3. Fallback Infalível: Buscar hashes de imagem no HTML (mesmo sob captcha)
        if not img_url or "susercontent.com" not in img_url:
            try:
                html = page.content()
                hashes = re.findall(r'br-11134207-[a-z0-9-]+', html) + re.findall(r'sg-11134201-[a-z0-9-]+', html)
                # Filtra hashes genéricos e banners de recomendação da shopee
                hashes_filtrados = [h for h in hashes if not h.startswith('br-11134207-7r98o-lxwr') and not h.startswith('br-11134207-7r98o-mccf') and not h.startswith('br-11134207-7r98o-m0kjw') and not h.startswith('br-11134207-81z1k-mgzon') and not h.startswith('br-11134207-7r98o-m9266')]
                if hashes_filtrados:
                    img_url = f"https://down-br.img.susercontent.com/file/{hashes_filtrados[0]}"
                    print(f"   🎯 Imagem encontrada via hash no HTML: {img_url}")
            except Exception as e:
                print(f"   ⚠️ Erro ao extrair hash: {e}")

        if img_url and img_url.startswith("http"):
            try:
                print(f"   📥 Baixando imagem: {img_url[:65]}...")
                r = requests.get(img_url, timeout=15)
                if len(r.content) > 5000:
                    with open(caminho_foto, "wb") as f_out:
                        f_out.write(r.content)
                    with Image.open(caminho_foto) as img:
                        img.verify()
                    print(f"   ✅ Foto salva e validada: {caminho_foto} ({len(r.content)} bytes)")
                    return caminho_foto
            except Exception as e:
                print(f"   ⚠️ Falha ao baixar/validar imagem: {e}")
                
    return None

def processar_lote(inicio=0, tamanho=5):
    todos_produtos = carregar_planilha()
    total = len(todos_produtos)
    fim = min(inicio + tamanho, total)
    
    print(f"==================================================")
    print(f"🚀 INICIANDO PROCESSAMENTO: ITENS {inicio + 1} ATÉ {fim} (DE {total})")
    print(f"==================================================")
    
    lote = todos_produtos[inicio:fim]
    processados = []
    
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=os.path.join(PASTA_BASE, "sessao_shopee"),
            headless=False,
            channel='chrome',
            args=['--disable-blink-features=AutomationControlled']
        )
        for i, item in enumerate(lote, start=inicio + 1):
            page = ctx.new_page()
            item_id = item['Item Id']
            nome_original = item['Item Name'].strip()
            preco_str = item['Price'].replace('"', '').replace('R$', '').strip()
            
            # Trata casos especiais como "1,3mil"
            if "mil" in preco_str:
                preco_num = preco_str.replace("mil", "").replace(",", ".")
                try:
                    preco_str = f"{float(preco_num)*1000:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                except Exception:
                    pass
            elif not preco_str.endswith("0") and len(preco_str.split(",")[-1]) == 1:
                preco_str = preco_str + "0"
                
            link_afiliado = item['Offer Link']
            link_produto = item['Product Link']
            nome_loja = item.get('Nome da loja', '').strip()
            
            # Limpeza do título
            titulo_limpo = " ".join(nome_original.split())
            if len(titulo_limpo) > 60:
                titulo_curto = titulo_limpo[:60].rsplit(" ", 1)[0]
            else:
                titulo_curto = titulo_limpo
                
            print(f"\n[{i}/{total}] Processando: {titulo_curto}")
            print(f"   💰 Preço: R$ {preco_str} | Loja: {nome_loja}")
            print(f"   🔗 Link: {link_afiliado}")
            
            # 1. Obter Foto
            foto_caminho = baixar_imagem_produto(page, link_produto, link_afiliado, item_id)
            page.close()
            if not foto_caminho:
                print(f"   ❌ ERRO: Não foi possível obter foto para {item_id}. Pulando envio.")
                continue
                
            # 2. Gerar Story 9:16
            caminho_story = os.path.join(PASTA_STORIES, f"story_lote_{i}_{item_id}.png")
            
            # Benefício de frete inteligente baseado no valor
            try:
                val_float = float(preco_str.replace(".", "").replace(",", "."))
                condicao_beneficio = "Cupom de Frete no App" if val_float < 50 else "Frete Grátis com Cupom"
            except Exception:
                condicao_beneficio = "Cupom de Frete no App"
            
            print(f"   🎨 Gerando Story 9:16 oficial...")
            criar_story_9_16(
                caminho_foto_produto=foto_caminho,
                titulo=titulo_curto,
                preco=preco_str,
                preco_antigo="",
                cupom=condicao_beneficio,
                caminho_saida=caminho_story
            )
            print(f"   ✅ Story salvo em: {caminho_story}")
            
            # 3. Legenda Perfeita para Telegram
            legenda = (
                f"🛍️ <b>{titulo_curto}</b>\n\n"
                f"💰 <b>Por apenas: R$ {preco_str}</b>\n"
                f"🚚 <b>Benefício:</b> {condicao_beneficio}\n"
                f"🏪 <b>Loja:</b> {nome_loja}\n\n"
                f"🔗 <b>Link Promocional (Toque e Copie):</b>\n{link_afiliado}"
            )
            
            # 4. Enviar para Telegram
            print(f"   📲 Enviando para o Telegram...")
            res_tg = enviar_para_telegram(caminho_story, legenda)
            print(f"   Resultado Telegram: {res_tg}")
            
            # 5. Guardar registro
            processados.append({
                "indice": i,
                "item_id": item_id,
                "titulo": titulo_curto,
                "preco": preco_str,
                "condicao": condicao_beneficio,
                "loja": nome_loja,
                "link_afiliado": link_afiliado,
                "caminho_imagem": foto_caminho,
                "caminho_story": caminho_story
            })
            
            time.sleep(3)
            
        ctx.close()
        
    # Atualizar fila geral de ofertas
    fila = []
    if os.path.exists(CAMINHO_FILA):
        try:
            with open(CAMINHO_FILA, "r", encoding="utf-8") as f:
                fila = json.load(f)
        except Exception:
            fila = []
            
    # Adicionar novos itens evitando duplicatas
    ids_existentes = {f.get("item_id") for f in fila if "item_id" in f}
    for p_item in processados:
        if p_item["item_id"] not in ids_existentes:
            fila.append(p_item)
            ids_existentes.add(p_item["item_id"])
        
    with open(CAMINHO_FILA, "w", encoding="utf-8") as f:
        json.dump(fila, f, indent=2, ensure_ascii=False)
        
    print("\n==================================================")
    print(f"🎉 LOTE {inicio + 1} A {fim} CONCLUÍDO COM SUCESSO!")
    print(f"Itens processados e entregues no Telegram: {len(processados)}")
    print("==================================================")
    return processados

if __name__ == "__main__":
    idx_inicio = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    qtd = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    processar_lote(idx_inicio, qtd)
