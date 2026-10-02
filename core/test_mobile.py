import sys
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

with sync_playwright() as p:
    device = p.devices['iPhone 14']
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(**device)
    page = context.new_page()
    page.goto('https://s.shopee.com.br/60S2ERYi05')
    page.wait_for_timeout(6000)
    print('URL:', page.url)
    print('Title:', page.title())
    tit = page.evaluate("() => document.querySelector('meta[property=\"og:title\"]')?.content || document.title")
    img = page.evaluate("() => document.querySelector('meta[property=\"og:image\"]')?.content || ''")
    desc = page.evaluate("() => document.querySelector('meta[property=\"og:description\"]')?.content || ''")
    print('Meta Tit:', tit)
    print('Meta Img:', img)
    print('Meta Desc:', desc[:100])
    page.screenshot(path='midia/item_5_mobile.png')
    browser.close()
