import requests
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

url = 'https://shopee.com.br/product/316945044/55260497129'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
}
r = requests.get(url, headers=headers)
print('Status:', r.status_code)
print('Length:', len(r.text))

m_title = re.search(r'<title>(.*?)</title>', r.text)
print('Title:', m_title.group(1) if m_title else 'None')

m_og = re.search(r'property="og:title" content="(.*?)"', r.text)
print('OG Title:', m_og.group(1) if m_og else 'None')

m_img = re.search(r'property="og:image" content="(.*?)"', r.text)
print('OG Img:', m_img.group(1) if m_img else 'None')

m_desc = re.search(r'property="og:description" content="(.*?)"', r.text)
print('OG Desc:', m_desc.group(1)[:200] if m_desc else 'None')
