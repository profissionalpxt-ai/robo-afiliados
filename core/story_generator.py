import os
import re
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
    
    # Suporte a fontes TrueType tanto em Windows quanto no Linux do Render
    fonte_bold = "C:/Windows/Fonts/arialbd.ttf"
    fonte_norm = "C:/Windows/Fonts/arial.ttf"
    fonte_black = "C:/Windows/Fonts/ariblk.ttf"

    if not os.path.exists(fonte_bold):
        for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
            if os.path.exists(f):
                fonte_bold = f
                fonte_black = f
                break

    if not os.path.exists(fonte_norm):
        for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
            if os.path.exists(f):
                fonte_norm = f
                break

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
    # Caixa de texto entre y=385 e y=520
    palavras = titulo.split()
    linha1, linha2 = [], []
    for p in palavras:
        if len(" ".join(linha1 + [p])) <= 24 and not linha2:
            linha1.append(p)
        elif len(" ".join(linha2 + [p])) <= 24:
            linha2.append(p)
            
    txt_l1 = " ".join(linha1)
    txt_l2 = " ".join(linha2) if linha2 else ""
    
    y_titulo = 395
    bbox1 = draw.textbbox((0, 0), txt_l1, font=font_titulo)
    draw.text(((largura - (bbox1[2] - bbox1[0])) // 2, y_titulo), txt_l1, font=font_titulo, fill=(18, 18, 20, 255))
    
    if txt_l2:
        y_titulo += 58
        bbox2 = draw.textbbox((0, 0), txt_l2, font=font_titulo)
        draw.text(((largura - (bbox2[2] - bbox2[0])) // 2, y_titulo), txt_l2, font=font_titulo, fill=(18, 18, 20, 255))

    # 2. FOTO DO PRODUTO (Centro do card branco)
    # Área disponível no card: y=530 até y=960 (largura máxima 680px, altura máxima 420px)
    max_w, max_h = 680, 420
    centro_y = 530 + (max_h // 2)
    
    foto_colada_com_sucesso = False
    if caminho_foto_produto and os.path.exists(caminho_foto_produto):
        try:
            # Validação estrita: abre e decodifica a imagem com Pillow
            with Image.open(caminho_foto_produto) as img_raw:
                prod_img = img_raw.convert("RGBA")
                
                # Redimensiona mantendo a proporção exata sem distorcer
                prod_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                
                px = (largura - prod_img.width) // 2
                py = centro_y - (prod_img.height // 2)
                
                # Cola a imagem do produto sobre o card branco
                imagem.paste(prod_img, (px, py), prod_img)
                foto_colada_com_sucesso = True
        except Exception as e:
            print(f"⚠️ Imagem corrompida ou inválida ignorada ({caminho_foto_produto}): {e}")

    # Se não houver foto válida ou arquivo corrompido, desenha badge estilizado de oferta
    if not foto_colada_com_sucesso:
        # Desenha uma área de destaque para não ficar buraco em branco
        draw.rounded_rectangle(
            [(250, 600), (830, 880)],
            radius=20,
            fill=(245, 248, 255, 255),
            outline=(210, 225, 250, 255),
            width=2
        )
        txt_destaque = "🛍️ OFERTA EXCLUSIVA" if not cupom else f"🎟️ CUPOM: {cupom}"
        try:
            font_destaque = ImageFont.truetype(fonte_bold, 40)
        except Exception:
            font_destaque = font_titulo
        bbox_d = draw.textbbox((0, 0), txt_destaque, font=font_destaque)
        draw.text(
            ((largura - (bbox_d[2] - bbox_d[0])) // 2, 720),
            txt_destaque,
            font=font_destaque,
            fill=(0, 85, 175, 255)
        )

    # 3. BLOCO DE PREÇOS (y=980 até y=1340)
    y_bloco = 990
    
    # Preço Antigo (De: R$ XX,XX)
    preco_antigo_str = str(preco_antigo or "").strip()
    if preco_antigo_str and re.search(r'\d', preco_antigo_str):
        p_antigo_limpo = re.sub(r'^R\$\s*', '', preco_antigo_str, flags=re.IGNORECASE).strip()
        txt_de = f"De: R$ {p_antigo_limpo}"
        bbox_de = draw.textbbox((0, 0), txt_de, font=font_de)
        dx = (largura - (bbox_de[2] - bbox_de[0])) // 2
        draw.text((dx, y_bloco), txt_de, font=font_de, fill=(110, 110, 110, 255))
        # Linha vermelha riscando o preço antigo
        draw.line([dx - 5, y_bloco + 20, dx + (bbox_de[2] - bbox_de[0]) + 5, y_bloco + 20], fill=(220, 40, 40, 255), width=3)
        y_bloco += 55

    # Preço Atual: "Por apenas:" (dourado) + "R$ XX,XX" (azul escuro)
    preco_str = str(preco or "").strip()
    tem_numero = bool(re.search(r'\d', preco_str))
    
    if tem_numero:
        preco_limpo = re.sub(r'^R\$\s*', '', preco_str, flags=re.IGNORECASE).strip()
        txt_label = "Por apenas: "
        txt_val = f"R$ {preco_limpo}"
        
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
    else:
        # Se não houver valor numérico (evita exibir "R$ Oferta")
        txt_destaque_oferta = "Confira a Oferta Especial"
        bbox_dest = draw.textbbox((0, 0), txt_destaque_oferta, font=font_por_label)
        dx = (largura - (bbox_dest[2] - bbox_dest[0])) // 2
        draw.text((dx, y_bloco), txt_destaque_oferta, font=font_por_label, fill=(245, 175, 25, 255))
        y_bloco += 60

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
    imagem.convert("RGB").save(caminho_saida, format="PNG", quality=95)
    return os.path.abspath(caminho_saida)
