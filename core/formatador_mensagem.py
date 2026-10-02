"""
Módulo de Formatação de Mensagens para WhatsApp e Instagram
Garante o layout idêntico ao modelo de alta conversão enviado pelo usuário:

[FOTO DO PRODUTO]
Título do Produto

R$ XX,XX - Condição

https://s.shopee.com.br/link

(ANÚNCIO)
"""

def formatar_mensagem_whatsapp(titulo: str, preco: str, link_afiliado: str, condicao: str = "Sem Juros", incluir_anuncio: bool = True) -> str:
    """
    Formata a mensagem para envio no WhatsApp com o produto.
    """
    # Limpa e formata o título para não ficar poluído com palavras-chave excessivas
    titulo_limpo = " ".join(titulo.split())
    if len(titulo_limpo) > 140:
        titulo_limpo = titulo_limpo[:137].rsplit(" ", 1)[0] + "..."
    
    # Formata condição de preço (ex: "Sem Juros", "Frete Grátis", "Cupom Ativo")
    linha_preco = f"R$ {preco}"
    if condicao:
        linha_preco += f" - {condicao}"
        
    partes = [
        titulo_limpo,
        "",
        linha_preco,
        "",
        link_afiliado.strip()
    ]
    
    if incluir_anuncio:
        partes.extend(["", "(ANÚNCIO)"])
        
    return "\n".join(partes)


def formatar_legenda_instagram(titulo: str, preco: str, categoria: str = "achadinhos") -> str:
    """
    Formata uma copy persuasiva para publicação nos Reels / Stories / Feed do Instagram.
    """
    hashtags = "#achadinhosshopee #achadinhos #shopee #comprinhas #achados #achadosshopee #promo #ofertas"
    
    copy = f"""🔥 ACHADINHO IMPERDÍVEL! 

👉 {titulo}
💰 Por apenas: R$ {preco}

📲 Para receber o link:
1️⃣ Comente "EU QUERO" aqui nos comentários
2️⃣ Ou acesse o link no topo da minha Bio (Grupo VIP de Cupons)

{hashtags}
"""
    return copy
