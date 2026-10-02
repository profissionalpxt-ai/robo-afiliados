import requests
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    page = browser.new_page()

    url_fone = 'https://s.shopee.com.br/60S0EfxCR4'
    print(f"Navegando até o fone: {url_fone}")
    page.goto(url_fone, timeout=30000)
    page.wait_for_timeout(4000)

    img_found = None
    meta = page.query_selector("meta[property='og:image']")
    if meta:
        img_found = meta.get_attribute("content")
        print("Meta og:image encontrada:", img_found)

    if not img_found:
        imgs = page.query_selector_all("img")
        for im in imgs:
            src = im.get_attribute("src") or ""
            if "susercontent.com/file/" in src:
                img_found = src
                print("Imagem do produto encontrada:", img_found)
                break

    if img_found:
        r = requests.get(img_found, timeout=15)
        caminho = "C:/Users/TRANSRAP05/Desktop/shopee-afiliado-bot/midia/fone.jpg"
        with open(caminho, "wb") as f:
            f.write(r.content)
        print("Fone salvo com sucesso em:", caminho)
    else:
        print("Imagem não encontrada")

    browser.close()
