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
    page.goto('https://s.shopee.com.br/60S2ERYi05')
    page.wait_for_timeout(3000)
    
    # Clica no idioma Português
    btn_pt = page.locator('text=Português (BR)').first
    if btn_pt.count():
        btn_pt.click()
        print('Clicou em Portugues BR!')
        page.wait_for_timeout(2000)
        
    btn_cookie = page.locator('text=Aceitar todos os cookies').first
    if btn_cookie.count():
        btn_cookie.click()
        print('Clicou em Aceitar cookies!')
        page.wait_for_timeout(2000)
        
    page.wait_for_timeout(4000)
    print('URL Final:', page.url)
    print('Titulo:', page.title())
    page.screenshot(path='midia/item_5_depois.png')
    ctx.close()
