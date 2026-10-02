import os
import sys
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

pasta = os.path.abspath('sessao_shopee')

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=pasta,
        headless=False,
        channel='chrome',
        args=['--disable-blink-features=AutomationControlled']
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto('https://s.shopee.com.br/2LYjrArKsN')
    page.wait_for_timeout(4000)
    
    title = page.title()
    meta_title = page.evaluate("() => document.querySelector('meta[property=\"og:title\"]')?.content || ''")
    meta_img = page.evaluate("() => document.querySelector('meta[property=\"og:image\"]')?.content || ''")
    
    ld_json = page.evaluate("() => Array.from(document.querySelectorAll('script[type=\"application/ld+json\"]')).map(s => s.innerText)")
    print('Title:', meta_title)
    print('Image:', meta_img)
    print('LD JSON count:', len(ld_json))
    for s in ld_json:
        print('LD:', s[:250])
        
    # Check body for price
    body_txt = page.evaluate("() => document.body.innerText")
    import re
    prices = re.findall(r'R\$\s*[\d\.,]+', body_txt)
    print('Prices found in body:', prices[:5])
    ctx.close()

