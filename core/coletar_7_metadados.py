import os
import sys
import json
import time
import requests
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

pasta = os.path.abspath('sessao_shopee')
os.makedirs(pasta, exist_ok=True)

PRODUTOS_7 = [
    {"idx": 1, "url": "https://s.shopee.com.br/2LYjrArKsN", "id": "55260497129"},
    {"idx": 2, "url": "https://s.shopee.com.br/2qV0SR7Ldm", "id": "20198093264"},
    {"idx": 3, "url": "https://s.shopee.com.br/gQVsYv6J3", "id": "22794290449"},
    {"idx": 4, "url": "https://s.shopee.com.br/30oQetBsRR", "id": "19299299965"},
    {"idx": 5, "url": "https://s.shopee.com.br/60S2ERYi05", "id": "23293909383"},
    {"idx": 6, "url": "https://s.shopee.com.br/7VGq1DkGJm", "id": "23397999673"},
    {"idx": 7, "url": "https://s.shopee.com.br/6L4sdCCCnf", "id": "19899586753"}
]

resultados = []

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=pasta, headless=False, channel='chrome')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    
    for p_item in PRODUTOS_7:
        print(f"Lendo [{p_item['idx']}/7] {p_item['url']}...")
        page.goto(p_item['url'])
        page.wait_for_timeout(3500)
        
        tit = page.evaluate("() => document.querySelector('meta[property=\"og:title\"]')?.content || document.title || ''")
        img = page.evaluate("() => document.querySelector('meta[property=\"og:image\"]')?.content || ''")
        desc = page.evaluate("() => document.querySelector('meta[property=\"og:description\"]')?.content || ''")
        
        tit_limpo = tit.replace(" | Shopee Brasil", "").replace("Shopee Brasil", "").strip()
        print(f"   -> Titulo: {tit_limpo[:60]}")
        print(f"   -> Img: {img[:60]}")
        
        resultados.append({
            "idx": p_item['idx'],
            "id": p_item['id'],
            "url": p_item['url'],
            "titulo": tit_limpo,
            "imagem": img,
            "desc": desc[:200]
        })
        time.sleep(1)
        
    ctx.close()

with open("midia/dados_7_shopee.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)
print("Salvo em midia/dados_7_shopee.json")
