import os
import sys
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

pasta = os.path.abspath('sessao_shopee')

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=pasta, headless=False, channel='chrome')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    
    for url in ['https://s.shopee.com.br/30oQetBsRR', 'https://s.shopee.com.br/60S2ERYi05']:
        print("Acessando:", url)
        page.goto(url)
        page.wait_for_timeout(6000)
        tit = page.evaluate("() => document.querySelector('meta[property=\"og:title\"]')?.content || document.title || ''")
        img = page.evaluate("() => document.querySelector('meta[property=\"og:image\"]')?.content || ''")
        desc = page.evaluate("() => document.querySelector('meta[property=\"og:description\"]')?.content || ''")
        print("URL final:", page.url)
        print("Title:", tit)
        print("Img:", img)
        print("Desc:", desc[:100])
        print("---")
    ctx.close()
