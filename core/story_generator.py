import os
from PIL import Image, ImageDraw, ImageFont

CAMINHO_TEMPLATE_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates", "template_story_base_clean.png"))

def criar_story_9_16(
    caminho_foto_produto: str, 
    titulo: str, 
    preco: str, 
    preco_antigo: str = "", 
    cupom: str = "", 
    condicao: str = "", 
    caminho_saida: str = ""
) -> str:
    """
    Gera o Story 9:16 oficial no template perfeito enviado pelo usuário:
    - Base com a Logo Oficial da Família, sacolas e confetes
    - Nome do produto no topo
    - Imagem do produto perfeitamente centralizada
    - Bloco de preço: De R$ X / Por apenas: R$ Y (dourado e azul)
    - Destaque para o código do CUPOM
    - Botão VER OFERTA + Área demarcada para a figurinha de link
    """
    if os.path.exists(CAMINHO_TEMPLATE_BASE):
        imagem = Image.open(CAMINHO_TEMPLATE_BASE).convert("RGBA")
    else:
        # Fallback caso não encontre
        imagem = Image.new("RGBA", (1080, 1920), (20, 20, 25, 255))
        
    draw = ImageDraw.Draw(imagem)
    largura, altura = imagem.size # 1080 x 1920
    
    fonte_bold = "C:/Windows/Fonts/arialbd.ttf"
    fonte_norm = "C:/Windows/Fonts/arial.ttf"
    fonte_black = "C:/Windows/Fonts/ariblk.ttf" # Arial Black para impacto
    if not os.path.exists(fonte_black):
        fonte_black = fonte_bold

    try:
        font_titulo = ImageFont.truetype(fonte_black, 48)
        font_de = ImageFont.truetype(fonte_norm, 36)
        font_por_label = ImageFont.truetype(fonte_black, 52)
        font_por_preco = ImageFont.truetype(fonte_black, 58)
        font_cupom = ImageFont.truetype(fonte_bold, 38)
        font_aviso = ImageFont.truetype(fonte_norm, 26)
    except Exception:
        font_titulo = font_de = font_por_label = font_por_preco = font_cupom = font_aviso = ImageFont.load_default()

    # 1. TÍTULO DO PRODUTO (Topo do card branco)
    # Caixa de texto entre y=405 e y=520
    palavras = titulo.split()
    linha1, linha2 = [], []
    for p in palavras:
        if len(" ".join(linha1 + [p])) <= 25 and not linha2:
            linha1.append(p)
        elif len(" ".join(linha2 + [p])) <= 25:
            linha2.append(p)
            
    txt_l1 = " ".join(linha1)
    txt_l2 = " ".join(linha2) if linha2 else ""
    
    y_titulo = 410
    bbox1 = draw.textbbox((0, 0), txt_l1, font=font_titulo)
    draw.text(((largura - (bbox1[2] - bbox1[0])) // 2, y_titulo), txt_l1, font=font_titulo, fill=(18, 18, 20, 255))
    
    if txt_l2:
        y_titulo += 55
        bbox2 = draw.textbbox((0, 0), txt_l2, font=font_titulo)
        draw.text(((largura - (bbox2[2] - bbox2[0])) // 2, y_titulo), txt_l2, font=font_titulo, fill=(18, 18, 20, 255))

    # 2. FOTO DO PRODUTO (Centro do card branco)
    # Área disponível: y=530 até y=960 (altura máxima 430px, largura máxima 650px)
    max_w, max_h = 650, 430
    centro_y = 530 + (max_h // 2)
    
    if os.path.exists(caminho_foto_produto):
        try:
            prod_img = Image.open(caminho_foto_produto).convert("RGBA")
            prod_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            px = (largura - prod_img.width) // 2
            py = centro_y - (prod_img.height // 2)
            imagem.paste(prod_img, (px, py), prod_img if prod_img.mode == 'RGBA' else None)
        except Exception as e:
            print("Erro ao carregar foto do produto:", e)

    # 3. BLOCO DE PREÇOS (y=980 até y=1340)
    y_bloco = 990
    
    # Preço Antigo (De: R$ XX,XX)
    if preco_antigo:
        txt_de = f"De: R$ {preco_antigo}"
        bbox_de = draw.textbbox((0, 0), txt_de, font=font_de)
        dx = (largura - (bbox_de[2] - bbox_de[0])) // 2
        draw.text((dx, y_bloco), txt_de, font=font_de, fill=(110, 110, 110, 255))
        # Linha vermelha riscando o preço antigo
        draw.line([dx - 5, y_bloco + 20, dx + (bbox_de[2] - bbox_de[0]) + 5, y_bloco + 20], fill=(220, 40, 40, 255), width=3)
        y_bloco += 55

    # Preço Atual: "Por apenas:" (dourado) + "R$ XX,XX" (azul escuro)
    txt_label = "Por apenas: "
    txt_val = f"R$ {preco}"
    
    bbox_label = draw.textbbox((0, 0), txt_label, font=font_por_label)
    bbox_val = draw.textbbox((0, 0), txt_val, font=font_por_preco)
    
    largura_total = (bbox_label[2] - bbox_label[0]) + (bbox_val[2] - bbox_val[0])
    inicio_x = (largura - largura_total) // 2
    
    # "Por apenas:" em Amarelo/Dourado do template
    draw.text((inicio_x, y_bloco), txt_label, font=font_por_label, fill=(245, 175, 25, 255))
    # "R$ XX,XX" em Azul Royal
    val_x = inicio_x + (bbox_label[2] - bbox_label[0])
    draw.text((val_x, y_bloco - 4), txt_val, font=font_por_preco, fill=(0, 85, 175, 255))
    y_bloco += 75

    # 4. CUPOM DE DESCONTO OU INSTRUÇÃO DE BENEFÍCIO
    if cupom:
        if any(palavra in cupom.lower() for palavra in ["ative", "selecione", "frete"]):
            txt_cupom = cupom
        else:
            txt_cupom = f"Utilize o cupom: {cupom}"
    else:
        txt_cupom = "Selecione o cupom de frete no carrinho"
        
    bbox_cupom = draw.textbbox((0, 0), txt_cupom, font=font_cupom)
    cx = (largura - (bbox_cupom[2] - bbox_cupom[0])) // 2
    draw.text((cx, y_bloco), txt_cupom, font=font_cupom, fill=(20, 20, 22, 255))
    y_bloco += 55

    # 5. AVISO LEGAL
    txt_aviso = "(Sujeito a alteração de preço ou estoque)"
    bbox_aviso = draw.textbbox((0, 0), txt_aviso, font=font_aviso)
    ax = (largura - (bbox_aviso[2] - bbox_aviso[0])) // 2
    draw.text((ax, y_bloco), txt_aviso, font=font_aviso, fill=(120, 120, 120, 255))

    # Salva o arquivo final
    if not caminho_saida:
        caminho_saida = os.path.join(os.path.dirname(__file__), "..", "stories_instagram", f"story_{abs(hash(titulo)) % 100000}.png")
        
    caminho_saida = os.path.normpath(caminho_saida)
    imagem.convert("RGB").save(caminho_saida)
    return os.path.abspath(caminho_saida)
