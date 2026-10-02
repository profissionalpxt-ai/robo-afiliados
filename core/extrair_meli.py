import re
import json
import urllib.parse
import requests

links = [
    'https://meli.la/12YPTw3',
    'https://meli.la/1jg6qRW',
    'https://meli.la/2vX25Yn',
    'https://meli.la/1F5Vhii',
    'https://meli.la/34d3Lek'
]

headers = {
    'User-Agent': 'MercadoLibre/10.0 (Android; 13; SM-G998B)',
    'x-platform': 'android'
}

for idx, link in enumerate(links, 1):
    try:
        r = requests.get(link, headers=headers, timeout=15)
        m = re.search(r'_n\.ctx\.r=({.*?});', r.text)
        if m:
            data = json.loads(m.group(1))
            comps = data.get('appProps', {}).get('pageProps', {}).get('data', {}).get('components', [])
            for c in comps:
                if c.get('id') == 'card-featured':
                    r_info = c.get('recommendation_data', {}).get('recommendation_info', {})
                    items = r_info.get('items', [])
                    if items:
                        meta = items[0].get('metadata', {})
                        url_p = meta.get('url_params', '')
                        real_url = ''
                        m_u = re.search(r'url=([^&]+)', url_p)
                        if m_u:
                            real_url = urllib.parse.unquote(m_u.group(1))
                            
                        # Preço e título
                        poly = items[0].get('polycard', {})
                        title = poly.get('title', {}).get('text', '')
                        price = poly.get('price', {}).get('current', {}).get('value', '')
                        
                        pic = items[0].get('pictures', {}).get('pictures', [])
                        img_id = pic[0].get('id', '') if pic else ''
                        img_url = f"https://http2.mlstatic.com/D_NQ_NP_{img_id}-O.webp" if img_id else ''

                        print(f"\n--- [{idx}/5] {link} ---")
                        print(f"Título: {title}")
                        print(f"Preço: R$ {price}")
                        print(f"URL Real: {real_url[:90]}")
                        print(f"Imagem: {img_url}")
    except Exception as e:
        print(f"Erro no link {link}: {e}")
