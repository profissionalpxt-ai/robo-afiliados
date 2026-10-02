import sys
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        viewport={'width': 1280, 'height': 800}
    )
    page = context.new_page()
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    url = 'https://shopee.com.br/product/316945044/55260497129'
    print(f"Acessando {url}...")
    page.goto(url)
    page.wait_for_timeout(6000)
    print("URL Final:", page.url)
    print("Titulo:", page.title())
    
    # Busca preco
    preco = ""
    for el in page.query_selector_all('div[class*="price"], span[class*="price"], div[class*="Price"], span[class*="Price"]'):
        txt = el.inner_text().strip()
        if "R$" in txt:
            preco = txt
            break
    print("Preco achado:", preco)
    browser.close()
