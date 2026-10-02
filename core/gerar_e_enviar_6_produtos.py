import os
import sys
import json
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram

PASTA_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA_STORIES = os.path.join(PASTA_BASE, "stories_instagram")
CAMINHO_FILA = os.path.join(PASTA_BASE, "fila", "ofertas_prontas.json")

PRODUTOS = [
    {
        "id": "item_1",
        "titulo": "Kit Estética Automotiva Vonixx Completo 7 Peças",
        "preco": "129,90",
        "preco_antigo": "179,90",
        "condicao": "Frete Grátis com Cupom",
        "link": "https://s.shopee.com.br/2LYjrArKsN",
        "foto": os.path.join(PASTA_BASE, "midia", "item_1.jpg"),
        "story": os.path.join(PASTA_STORIES, "story_kit_vonixx.png")
    },
    {
        "id": "item_2",
        "titulo": "Capacete New Liberty 3 Personalizado LS2 DRAZE",
        "preco": "89,90",
        "preco_antigo": "139,90",
        "condicao": "Sem Juros",
        "link": "https://s.shopee.com.br/2qV0SR7Ldm",
        "foto": os.path.join(PASTA_BASE, "midia", "item_2.jpg"),
        "story": os.path.join(PASTA_STORIES, "story_capacete_ls2.png")
    },
    {
        "id": "item_3",
        "titulo": "Bomba de Ar Compressor Portátil 4 em 1 PowerBank",
        "preco": "74,90",
        "preco_antigo": "119,90",
        "condicao": "Cupom de Frete no Carrinho",
        "link": "https://s.shopee.com.br/gQVsYv6J3",
        "foto": os.path.join(PASTA_BASE, "midia", "item_3.jpg"),
        "story": os.path.join(PASTA_STORIES, "story_compressor_portatil.png")
    },
    {
        "id": "item_4",
        "titulo": "Kit Mobilador Completo 7 Peças Teclado e Mouse",
        "preco": "78,90",
        "preco_antigo": "119,90",
        "condicao": "Sem Juros",
        "link": "https://s.shopee.com.br/30oQetBsRR",
        "foto": os.path.join(PASTA_BASE, "midia", "item_4.jpg"),
        "story": os.path.join(PASTA_STORIES, "story_kit_mobilador.png")
    },
    {
        "id": "item_6",
        "titulo": "Kit 6 Peças Roupa Infantil Menina 3 Conjuntos",
        "preco": "49,90",
        "preco_antigo": "79,90",
        "condicao": "Cupom de Frete no Carrinho",
        "link": "https://s.shopee.com.br/7VGq1DkGJm",
        "foto": os.path.join(PASTA_BASE, "midia", "item_6.jpg"),
        "story": os.path.join(PASTA_STORIES, "story_kit_infantil.png")
    },
    {
        "id": "item_7",
        "titulo": "Fone de Ouvido Bluetooth Sem Fio Pop-Up Premium",
        "preco": "34,90",
        "preco_antigo": "59,90",
        "condicao": "Cupom de Frete no Carrinho",
        "link": "https://s.shopee.com.br/6L4sdCCCnf",
        "foto": os.path.join(PASTA_BASE, "midia", "item_7.jpg"),
        "story": os.path.join(PASTA_STORIES, "story_fone_popup.png")
    }
]

# Carregar fila existente
fila = []
if os.path.exists(CAMINHO_FILA):
    try:
        with open(CAMINHO_FILA, "r", encoding="utf-8") as f:
            fila = json.load(f)
    except Exception:
        fila = []

# Filtrar itens que já estavam na fila com título genérico 'Consulte Oferta'
fila_limpa = [item for item in fila if "Consulte Oferta" not in item.get("preco", "") and "| Ofertas" not in item.get("titulo", "")]

print("Gerando stories e enviando para o Telegram...")

for p in PRODUTOS:
    print(f"\n🎨 Processando: {p['titulo']} (R$ {p['preco']})...")
    
    # 1. Gerar Story oficial 9:16 com caixinha limpa
    criar_story_9_16(
        caminho_foto_produto=p['foto'],
        titulo=p['titulo'],
        preco=p['preco'],
        preco_antigo=p['preco_antigo'],
        cupom=p['condicao'],
        caminho_saida=p['story']
    )
    print(f"   Story salvo em: {p['story']}")
    
    # 2. Formatar legenda elegante com link pronto para cópia
    legenda = (
        f"🛍️ <b>{p['titulo']}</b>\n\n"
        f"💰 <b>Por apenas: R$ {p['preco']}</b>"
    )
    if p['preco_antigo']:
        legenda += f" <i>(De: R$ {p['preco_antigo']})</i>"
    legenda += (
        f"\n🚚 <b>Benefício:</b> {p['condicao']}\n\n"
        f"🔗 <b>Link de Afiliado (Toque e Copie):</b>\n{p['link']}"
    )
    
    # 3. Disparar no Telegram
    res_tg = enviar_para_telegram(p['story'], legenda)
    print(f"   📲 Telegram: {res_tg}")
    
    # 4. Adicionar à fila do WhatsApp
    fila_limpa.append({
        "titulo": p['titulo'],
        "preco": p['preco'],
        "preco_antigo": p['preco_antigo'],
        "condicao": p['condicao'],
        "link_afiliado": p['link'],
        "caminho_imagem": p['foto'],
        "caminho_story": p['story']
    })
    
    time.sleep(2)

# Salvar fila atualizada
with open(CAMINHO_FILA, "w", encoding="utf-8") as f:
    json.dump(fila_limpa, f, indent=2, ensure_ascii=False)

print(f"\n✅ Total de {len(PRODUTOS)} produtos enviados ao Telegram com sucesso!")
print(f"📦 Total atual na fila do WhatsApp: {len(fila_limpa)} ofertas.")
