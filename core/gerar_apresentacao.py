import os
from PIL import Image, ImageDraw, ImageFont

CAMINHO_LOGO = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\logo_achadinhos_familia.jpg"
PASTA_STORIES = r"C:\Users\TRANSRAP05\Desktop\shopee-afiliado-bot\stories_instagram"

def criar_post_apresentacao():
    # Formato Feed Retrato 1080x1350 (formato que mais ocupa tela e gera engajamento no Instagram)
    largura = 1080
    altura = 1350
    
    # Fundo moderno em degradê escuro sofisticado
    imagem = Image.new("RGBA", (largura, altura), (14, 16, 22, 255))
    draw = ImageDraw.Draw(imagem)
    
    for y in range(altura):
        r = int(14 + (24 - 14) * (y / altura))
        g = int(16 + (20 - 16) * (y / altura))
        b = int(22 + (32 - 22) * (y / altura))
        draw.line([(0, y), (largura, y)], fill=(r, g, b, 255))

    fonte_bold = "C:/Windows/Fonts/arialbd.ttf"
    fonte_norm = "C:/Windows/Fonts/arial.ttf"
    fonte_black = "C:/Windows/Fonts/ariblk.ttf"

    font_tag = ImageFont.truetype(fonte_bold, 30)
    font_titulo = ImageFont.truetype(fonte_black, 48)
    font_sub = ImageFont.truetype(fonte_norm, 32)
    font_card_tit = ImageFont.truetype(fonte_black, 36)
    font_card_desc = ImageFont.truetype(fonte_norm, 26)
    font_rodape = ImageFont.truetype(fonte_bold, 34)

    # 1. LOGO DA FAMÍLIA CIRCULAR NO TOPO
    y_logo = 70
    tam_logo = 260
    if os.path.exists(CAMINHO_LOGO):
        logo_img = Image.open(CAMINHO_LOGO).convert("RGBA")
        logo_img = logo_img.resize((tam_logo, tam_logo), Image.Resampling.LANCZOS)
        
        mascara = Image.new('L', (tam_logo, tam_logo), 0)
        draw_m = ImageDraw.Draw(mascara)
        draw_m.ellipse((0, 0, tam_logo, tam_logo), fill=255)
        
        lx = (largura - tam_logo) // 2
        imagem.paste(logo_img, (lx, y_logo), mascara)
        
        # Borda dourada/laranja brilhante
        draw.ellipse([lx - 4, y_logo - 4, lx + tam_logo + 4, y_logo + tam_logo + 4], outline=(245, 166, 35, 255), width=5)

    # 2. TÍTULOS DE BOAS-VINDAS
    y_textos = y_logo + tam_logo + 35
    
    tag_txt = "SEJAM MUITO BEM-VINDOS!"
    b_tag = draw.textbbox((0, 0), tag_txt, font=font_tag)
    draw.text(((largura - (b_tag[2] - b_tag[0])) // 2, y_textos), tag_txt, font=font_tag, fill=(245, 175, 25, 255))
    
    y_textos += 50
    tit_txt = "ACHADINHOS DA FAMÍLIA"
    b_tit = draw.textbbox((0, 0), tit_txt, font=font_titulo)
    draw.text(((largura - (b_tit[2] - b_tit[0])) // 2, y_textos), tit_txt, font=font_titulo, fill=(255, 255, 255, 255))

    y_textos += 60
    sub_txt = "O seu novo cantinho diário de economia e cupons reais"
    b_sub = draw.textbbox((0, 0), sub_txt, font=font_sub)
    draw.text(((largura - (b_sub[2] - b_sub[0])) // 2, y_textos), sub_txt, font=font_sub, fill=(180, 185, 195, 255))

    # 3. OS 3 PILARES (CARDS VISUAIS)
    y_cards = y_textos + 75
    cards = [
        {
            "icone": "🏠",
            "titulo": "CASA & COZINHA",
            "desc": "Achadinhos que facilitam sua rotina e deixam o lar mais prático.",
            "cor_borda": (238, 77, 45, 255) # Laranja
        },
        {
            "icone": "🚗",
            "titulo": "AUTO & GARAGEM",
            "desc": "Acessórios, cuidados automotivos e ferramentas com preço justo.",
            "cor_borda": (0, 150, 255, 255) # Azul
        },
        {
            "icone": "⚡",
            "titulo": "ELETRÔNICOS & TECH",
            "desc": "Gadgets úteis, fones, cabos e novidades que realmente valem a pena.",
            "cor_borda": (245, 175, 25, 255) # Dourado
        }
    ]

    card_w = 900
    card_h = 135
    cx = (largura - card_w) // 2

    for c in cards:
        # Fundo do card
        draw.rounded_rectangle([cx, y_cards, cx + card_w, y_cards + card_h], radius=22, fill=(24, 28, 38, 255), outline=c["cor_borda"], width=2)
        
        # Título
        draw.text((cx + 40, y_cards + 25), c["titulo"], font=font_card_tit, fill=(255, 255, 255, 255))
        # Descrição
        draw.text((cx + 40, y_cards + 78), c["desc"], font=font_card_desc, fill=(170, 175, 190, 255))
        
        y_cards += card_h + 25

    # 4. RODAPÉ COM CHAMADA
    y_rodape = y_cards + 20
    c_btn_w = 900
    c_btn_h = 95
    bx = (largura - c_btn_w) // 2
    draw.rounded_rectangle([bx, y_rodape, bx + c_btn_w, y_rodape + c_btn_h], radius=48, fill=(245, 175, 25, 255))
    
    txt_btn = "SIGA E ENTRE NO GRUPO VIP NA BIO!"
    b_btn = draw.textbbox((0, 0), txt_btn, font=font_rodape)
    draw.text((bx + (c_btn_w - (b_btn[2] - b_btn[0])) // 2, y_rodape + 28), txt_btn, font=font_rodape, fill=(14, 16, 22, 255))

    caminho_saida = os.path.join(PASTA_STORIES, "post_apresentacao_familia.png")
    caminho_saida = os.path.normpath(caminho_saida)
    imagem.convert("RGB").save(caminho_saida)
    return caminho_saida

if __name__ == "__main__":
    res = criar_post_apresentacao()
    print("Post de apresentação criado em:", res)
