import os
import re
import json
import requests
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

def resolver_redirecionamento(url: str) -> str:
    """Resolve links curtos da Shopee (ex: s.shopee.com.br ou shope.ee)"""
    try:
        resp = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=10)
        return resp.url
    except Exception:
        return url

def extrair_shop_item_id(url: str):
    """Extrai shopid e itemid da URL da Shopee"""
    # Padrão: -i.123456.7891011 ou product/123456/7891011
    padrao1 = re.search(r"-i\.(\d+)\.(\d+)", url)
    if padrao1:
        return padrao1.group(1), padrao1.group(2)
        
    padrao2 = re.search(r"product/(\d+)/(\d+)", url)
    if padrao2:
        return padrao2.group(1), padrao2.group(2)
        
    padrao3 = re.search(r"itemid=(\d+)&shopid=(\d+)", url)
    if padrao3:
        return padrao3.group(2), padrao3.group(1)
        
    return None, None

def extrair_detalhes_shopee(url_original: str, pasta_midia: str = "midia", pasta_videos: str = "videos_instagram") -> dict:
    """
    Extrai informações completas do produto:
    - Título
    - Preço
    - Foto em alta resolução (salva em pasta_midia)
    - Vídeo do anúncio (salva em pasta_videos se existir)
    """
    url_final = resolver_redirecionamento(url_original)
    shopid, itemid = extrair_shop_item_id(url_final)
    
    dados = {
        "url_original": url_original,
        "url_final": url_final,
        "titulo": "Produto Shopee",
        "preco": "0,00",
        "preco_antigo": "",
        "imagem_url": "",
        "caminho_imagem": "",
        "video_url": "",
        "caminho_video": "",
        "sucesso": False,
        "mensagem": ""
    }
    
    os.makedirs(pasta_midia, exist_ok=True)
    os.makedirs(pasta_videos, exist_ok=True)
    
    # Tentativa 1: API Oficial Pública da Shopee
    if shopid and itemid:
        api_url = f"https://shopee.com.br/api/v4/item/get?itemid={itemid}&shopid={shopid}"
        try:
            r = requests.get(api_url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                res = r.json()
                data = res.get("data")
                if data:
                    dados["titulo"] = data.get("name", "Produto Shopee")
                    
                    # Preço na Shopee vem multiplicado por 100000
                    preco_raw = data.get("price", 0) / 100000
                    dados["preco"] = f"{preco_raw:.2f}".replace(".", ",")
                    
                    if data.get("price_before_discount"):
                        p_antigo = data.get("price_before_discount", 0) / 100000
                        dados["preco_antigo"] = f"{p_antigo:.2f}".replace(".", ",")
                    
                    # Foto principal
                    imagem_hash = data.get("image")
                    if not imagem_hash and data.get("images"):
                        imagem_hash = data.get("images")[0]
                        
                    if imagem_hash:
                        dados["imagem_url"] = f"https://down-br.img.susercontent.com/file/{imagem_hash}"
                        caminho_img = os.path.join(pasta_midia, f"prod_{itemid}.jpg")
                        try:
                            r_img = requests.get(dados["imagem_url"], timeout=10)
                            with open(caminho_img, "wb") as f:
                                f.write(r_img.content)
                            dados["caminho_imagem"] = os.path.abspath(caminho_img)
                        except Exception:
                            pass
                            
                    # Vídeo do produto
                    videos = data.get("video_info_list", [])
                    if videos and len(videos) > 0:
                        v_info = videos[0]
                        v_formats = v_info.get("default_format", {})
                        dados["video_url"] = v_formats.get("url", "")
                        if dados["video_url"]:
                            caminho_vid = os.path.join(pasta_videos, f"reels_{itemid}.mp4")
                            try:
                                r_vid = requests.get(dados["video_url"], timeout=30)
                                with open(caminho_vid, "wb") as f:
                                    f.write(r_vid.content)
                                dados["caminho_video"] = os.path.abspath(caminho_vid)
                            except Exception:
                                pass
                                
                    dados["sucesso"] = True
                    return dados
        except Exception as e:
            dados["mensagem"] = str(e)

    # Tentativa 2: Fallback via meta tags OpenGraph da página
    try:
        r = requests.get(url_final, headers=HEADERS, timeout=10)
        html = r.text
        
        # Título
        m_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if m_title:
            dados["titulo"] = m_title.group(1).replace(" | Shopee Brasil", "").strip()
            
        # Imagem
        m_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if m_img:
            dados["imagem_url"] = m_img.group(1)
            nome_arq = f"prod_fallback_{abs(hash(url_final)) % 100000}.jpg"
            caminho_img = os.path.join(pasta_midia, nome_arq)
            try:
                r_img = requests.get(dados["imagem_url"], timeout=10)
                with open(caminho_img, "wb") as f:
                    f.write(r_img.content)
                dados["caminho_imagem"] = os.path.abspath(caminho_img)
            except Exception:
                pass
                
        dados["sucesso"] = bool(dados["titulo"] and dados["caminho_imagem"])
    except Exception as e:
        dados["mensagem"] = str(e)
        
    return dados
