import csv
import os
import requests
import sys
import time
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

csv_path = 'input_planilhas/BatchProductLinks20260930090819-a3e7fa514b494740b14286a9caf19920.csv'
items = []
with open(csv_path, mode='r', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        items.append(row)

os.makedirs('midia', exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir='sessao_shopee', headless=False, channel='chrome')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    
    # Garantir que aceita cookies ou fecha modal se aparecer
    page.goto("https://shopee.com.br")
    page.wait_for_timeout(3000)
    
    for it in items:
        item_id = it['Item Id']
        nome = it['Item Name']
        preco = it['Price']
        url = it['Product Link']
        caminho_foto = os.path.abspath(f"midia/prod_{item_id}.jpg")
        
        # Se for o item 1 (fone), já temos item_7.jpg
        if item_id == "19899586753" and os.path.exists("midia/item_7.jpg"):
            with open("midia/item_7.jpg", "rb") as f_src, open(caminho_foto, "wb") as f_dst:
                f_dst.write(f_src.read())
            print(f"✅ [19899586753] Fone de Ouvido: Foto pronta (copiada de item_7.jpg)")
            continue
            
        if os.path.exists(caminho_foto) and os.path.getsize(caminho_foto) > 5000:
            print(f"✅ [{item_id}] {nome[:35]}: Foto já salva ({os.path.getsize(caminho_foto)} bytes)")
            continue
            
        print(f"\n🔄 Buscando foto para: {nome[:40]}...")
        page.goto(url)
        page.wait_for_timeout(5000)
        
        # Tenta pegar metadados ou imagem da galeria
        img_url = ""
        meta_img = page.locator('meta[property="og:image"]').first
        if meta_img.count() > 0:
            img_url = meta_img.get_attribute("content") or ""
            
        if not img_url:
            for selector in ['img[src*="susercontent.com"]', 'img[src*="down-br"]']:
                loc = page.locator(selector).first
                if loc.count() > 0:
                    src = loc.get_attribute("src") or ""
                    if "susercontent.com" in src:
                        img_url = src
                        break
                        
        print(f"   URL Imagem: {img_url}")
        if img_url and img_url.startswith("http"):
            try:
                r = requests.get(img_url, timeout=10)
                if len(r.content) > 5000:
                    with open(caminho_foto, 'wb') as f_img:
                        f_img.write(r.content)
                    print(f"   ✅ Foto salva em: {caminho_foto} ({len(r.content)} bytes)")
            except Exception as e:
                print(f"   ❌ Erro ao baixar foto: {e}")
                
    ctx.close()

print("\n🚀 Todas as fotos verificadas!")
