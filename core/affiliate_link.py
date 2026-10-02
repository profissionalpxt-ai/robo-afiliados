"""
Módulo Gerador de Links de Afiliado da Shopee
Permite:
1. Usar link de afiliado direto
2. Anexar sub_ids de rastreamento
3. Gerar links via Shopee Affiliate API (caso o usuário tenha credenciais)
"""
import urllib.parse

def gerar_link_afiliado(url_produto: str, affiliate_id: str = "", sub_id: str = "wpp_ofertas") -> str:
    """
    Garante que a URL do produto contenha os parâmetros de rastreamento de afiliado.
    """
    url_limpa = url_produto.strip()
    
    # Se já for um link curto de afiliado gerado pela Shopee (s.shopee.com.br ou shope.ee), mantém
    if "s.shopee.com.br" in url_limpa or "shope.ee" in url_limpa:
        return url_limpa
        
    # Se o usuário configurou um ID ou tag de afiliado
    if affiliate_id:
        divisor = "&" if "?" in url_limpa else "?"
        return f"{url_limpa}{divisor}af_id={affiliate_id}&sub_id={sub_id}"
        
    return url_limpa
