import requests
import re

url = 'https://lista.mercadolivre.com.br/kit-mobilador-teclado-mouse-celular'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
r = requests.get(url, headers=headers)
m = re.findall(r'https://http2\.mlstatic\.com/D_NQ_NP_[^\"]+\.webp', r.text)
if m:
    r_img = requests.get(m[0])
    with open('midia/item_4.jpg', 'wb') as f:
        f.write(r_img.content)
    print(f"Salvo item_4.jpg: {len(r_img.content)} bytes")
else:
    print("Nenhuma imagem encontrada")
