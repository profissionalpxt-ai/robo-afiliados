import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram

items = [
    {
        'idx': 1,
        'titulo': 'Controle Sem Fio Manete Bluetooth Joystick Para',
        'preco': '46,66',
        'preco_antigo': '120,00',
        'cupom': 'R$ 41,99 com Cupom no App',
        'link': 'https://meli.la/12YPTw3',
        'foto': 'midia/meli_1.webp',
        'story': 'stories_instagram/story_meli_1.png'
    },
    {
        'idx': 2,
        'titulo': 'Sofá Retrátil Reclinável 4 Lugares Molas Ensacadas',
        'preco': '1648,00',
        'preco_antigo': '2699,00',
        'cupom': 'Frete Grátis pelo FULL',
        'link': 'https://meli.la/1jg6qRW',
        'foto': 'midia/meli_2.webp',
        'story': 'stories_instagram/story_meli_2.png'
    },
    {
        'idx': 3,
        'titulo': 'Copo Térmico Gigante 1,2l Inox Com Tampa',
        'preco': '48,99',
        'preco_antigo': '76,99',
        'cupom': 'Frete Grátis pelo FULL',
        'link': 'https://meli.la/2vX25Yn',
        'foto': 'midia/meli_3.webp',
        'story': 'stories_instagram/story_meli_3.png'
    },
    {
        'idx': 4,
        'titulo': 'Pano de Prato Atoalhado Atacado Laune Gourmet',
        'preco': '40,24',
        'preco_antigo': '76,99',
        'cupom': '5% OFF com Cupom',
        'link': 'https://meli.la/1F5Vhii',
        'foto': 'midia/meli_4.webp',
        'story': 'stories_instagram/story_meli_4.png'
    },
    {
        'idx': 5,
        'titulo': '3 Manta Microfibra Coberta Casal Solf 2,00',
        'preco': '69,90',
        'preco_antigo': '78,90',
        'cupom': 'Frete Grátis pelo FULL',
        'link': 'https://meli.la/34d3Lek',
        'foto': 'midia/meli_5.webp',
        'story': 'stories_instagram/story_meli_5.png'
    }
]

for it in items:
    caminho_foto = os.path.abspath(it['foto'])
    caminho_story = os.path.abspath(it['story'])
    
    criar_story_9_16(
        caminho_foto_produto=caminho_foto,
        titulo=it['titulo'],
        preco=it['preco'],
        preco_antigo=it['preco_antigo'],
        cupom=it['cupom'],
        caminho_saida=caminho_story
    )
    
    legenda = (
        f"🎨 <b>Novo Story Limpo (Sem frase no link)</b>\n\n"
        f"📦 <b>{it['titulo']}</b>\n"
        f"💰 <b>R$ {it['preco']}</b>\n\n"
        f"🔗 <b>Link para colocar no Story (Toque e Copie):</b>\n{it['link']}"
    )
    res = enviar_para_telegram(caminho_story, legenda)
    print(f"Item {it['idx']} enviado ao Telegram: {res}")
    time.sleep(2)

print("Todos os 5 stories atualizados foram enviados ao Telegram!")
