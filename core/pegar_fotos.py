import requests
from playwright.sync_api import sync_playwright

urls = {
    "fone": "https://shopee.com.br/product/1103946075/19899586753",
    "potes": "https://shopee.com.br/product/1662234915/58213382206"
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    page = browser.new_page()

    for nome, url in urls.items():
        print(f"Buscando {nome}: {url}")
        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(4000)
            meta = page.query_selector('meta[property="og:image"]')
            if meta:
                img_url = meta.get_attribute("content")
                print(f"URL Imagem {nome}: {img_url}")
                if img_url:
                    r = requests.get(img_url, timeout=15)
                    caminho = f"C:/Users/TRANSRAP05/Desktop/shopee-afiliado-bot/midia/{nome}.jpg"
                    with open(caminho, "wb") as f:
                        f.write(r.content)
                    print(f"Salvo em {caminho}")
            else:
                print(f"Meta tag não encontrada para {nome}")
        except Exception as e:
            print(f"Erro em {nome}: {e}")

    browser.close()
