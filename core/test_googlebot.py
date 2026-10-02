import requests
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
r = requests.get('https://s.shopee.com.br/60S2ERYi05', headers=headers, allow_redirects=True, timeout=10)
print('Status:', r.status_code)
print('URL:', r.url)

m_title = re.search(r'<title>(.*?)</title>', r.text)
if m_title:
    print('Title:', m_title.group(1))

m_og = re.search(r'property="og:title" content="(.*?)"', r.text)
if m_og:
    print('OG Title:', m_og.group(1))

m_img = re.search(r'property="og:image" content="(.*?)"', r.text)
with open('midia/googlebot_dump.html', 'w', encoding='utf-8') as out:
    out.write(r.text)
print('Salvo googlebot_dump.html')

