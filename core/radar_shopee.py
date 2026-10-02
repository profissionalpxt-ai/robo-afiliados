import os
import sys
import re
import json
import time
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram

PASTA_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA_MIDIA = os.path.join(PASTA_BASE, "midia")
PASTA_STORIES = os.path.join(PASTA_BASE, "stories_instagram")
ARQUIVO_VISTOS = os.path.join(PASTA_BASE, "config", "vistos_radar.json")
CAMINHO_FILA = os.path.join(PASTA_BASE, "fila", "ofertas_prontas.json")

os.makedirs(PASTA_MIDIA, exist_ok=True)
os.makedirs(PASTA_STORIES, exist_ok=True)
os.makedirs(os.path.dirname(ARQUIVO_VISTOS), exist_ok=True)

# Canais públicos monitorados
CANAIS_RADAR = [
    "escolhasegura",
    "casaricadeoracao",
    "shopeebrcupom",
    "Automa_Web_Ofertas_01",
    "ofertasgamerandre"
]

AFFILIATE_PID = "an_18316781247"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def carregar_vistos() -> set:
    if os.path.exists(ARQUIVO_VISTOS):
        try:
            with open(ARQUIVO_VISTOS, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def salvar_vistos(vistos: set):
    try:
        with open(ARQUIVO_VISTOS, "w", encoding="utf-8") as f:
            json.dump(list(vistos)[-500:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar vistos: {e}")

def converter_link_shopee(link_curto: str) -> str:
    """Expande o link da Shopee do concorrente e injeta o ID de afiliado do usuário"""
    try:
        resp = requests.get(link_curto, headers=HEADERS, allow_redirects=True, timeout=12)
        url_destino = resp.url
        
        parsed = urlparse(url_destino)
        query = parse_qs(parsed.query)
        
        # Injeta os parâmetros de afiliado do usuário
        query["mmp_pid"] = [AFFILIATE_PID]
        query["utm_source"] = [AFFILIATE_PID]
        query["utm_medium"] = ["affiliates"]
        query["utm_campaign"] = ["radar_achadinhos"]
        
        nova_query = urlencode(query, doseq=True)
        url_final = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, nova_query, parsed.fragment))
        return url_final
    except Exception:
        # Se falhar a expansão, anexa os parâmetros diretamente
        sep = "&" if "?" in link_curto else "?"
        return f"{link_curto}{sep}mmp_pid={AFFILIATE_PID}&utm_source={AFFILIATE_PID}&utm_medium=affiliates"

def varrer_canais() -> list:
    """Varre todos os canais e processa novas ofertas e cupons da Shopee"""
    vistos = carregar_vistos()
    novas_ofertas = []
    
    print("\n📡 [RADAR] Iniciando varredura nos 5 canais do Telegram...")
    
    for canal in CANAIS_RADAR:
        url_canal = f"https://t.me/s/{canal}"
        try:
            r = requests.get(url_canal, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
                
            html = r.text
            
            # Extrai blocos de mensagens
            blocos = re.findall(r'<div class="tgme_widget_message_wrap[^"]*"[^>]*data-post="([^"]+)"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
            if not blocos:
                # Fallback alternativo para extrair data-post
                posts = re.findall(r'data-post="([^"]+)"', html)
                blocos = [(p, html) for p in posts[-15:]]
                
            for post_id, conteudo in blocos[-8:]:
                if post_id in vistos:
                    continue
                    
                # Procura links da Shopee
                shopee_links = re.findall(r'https://s\.shopee\.com\.br/[a-zA-Z0-9]+', conteudo) + re.findall(r'https://shopee\.com\.br/[^\s"\'<>]+', conteudo)
                if not shopee_links:
                    continue
                    
                link_concorrente = shopee_links[0]
                
                # Extrai texto limpo
                m_text = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', conteudo, re.DOTALL)
                texto_bruto = m_text.group(1) if m_text else conteudo
                texto_limpo = re.sub(r'<[^>]+>', ' ', texto_bruto)
                texto_limpo = " ".join(texto_limpo.split())
                
                # Extrai título (primeiras palavras ou primeira linha)
                primeira_linha = texto_limpo.split("POR:")[0].split("DE:")[0].split("R$")[0].strip()
                # Remove emojis do início
                titulo = re.sub(r'^[^\w\s]+', '', primeira_linha).strip()
                if len(titulo) > 55:
                    titulo = titulo[:55].rsplit(" ", 1)[0]
                if len(titulo) < 5:
                    titulo = "Achadinho Especial Shopee"
                    
                # Extrai Preço
                preco = ""
                m_preco = re.search(r'(?:POR|Por apenas|Preço):\s*(?:R\$\s*)?([\d.,]+)', texto_limpo, re.IGNORECASE)
                if not m_preco:
                    m_preco = re.search(r'R\$\s*([\d.,]+)', texto_limpo)
                if m_preco:
                    preco = m_preco.group(1).replace(".", "").replace(",", ".")
                    try:
                        preco = f"{float(preco):.2f}".replace(".", ",")
                    except Exception:
                        preco = m_preco.group(1)
                else:
                    preco = "Oferta"
                    
                # Extrai Cupom se houver
                cupom = ""
                m_cupom = re.search(r'(?:CUPOM|Cupom):\s*([A-Za-z0-9_-]+)', texto_limpo)
                if m_cupom:
                    cupom = m_cupom.group(1).strip()
                    
                # Extrai Foto do post no Telegram CDN
                m_foto = re.search(r"background-image:url\('([^']+)'\)", conteudo)
                foto_url = m_foto.group(1) if m_foto else ""
                
                if not foto_url or "emoji" in foto_url:
                    # Tenta achar no CDN geral da mensagem
                    cdn_matches = [u for u in re.findall(r'https://cdn\d*\.telesco\.pe/file/[^\s"\')]+\.jpg', conteudo) if 'emoji' not in u]
                    if cdn_matches:
                        foto_url = cdn_matches[0]
                        
                print(f"\n🔥 [NOVA OFERTA @{canal}]: {titulo}")
                print(f"   💰 Preço: R$ {preco} | Cupom: {cupom}")
                print(f"   🔗 Link Concorrente: {link_concorrente}")
                
                # Converte para link do usuário
                link_afiliado_usuario = converter_link_shopee(link_concorrente)
                print(f"   💎 Seu Link de Afiliado: {link_afiliado_usuario[:80]}...")
                
                caminho_foto_local = ""
                if foto_url and foto_url.startswith("http"):
                    try:
                        r_foto = requests.get(foto_url, timeout=15)
                        if len(r_foto.content) > 5000:
                            caminho_foto_local = os.path.join(PASTA_MIDIA, f"radar_{post_id.replace('/', '_')}.jpg")
                            with open(caminho_foto_local, "wb") as f_img:
                                f_img.write(r_foto.content)
                    except Exception as e:
                        print(f"   ⚠️ Falha ao baixar foto: {e}")
                        
                # Gera Story 9:16 com a Logo Oficial
                caminho_story = ""
                beneficio = f"Cupom: {cupom}" if cupom else "Cupom de Frete no App"
                
                if caminho_foto_local and os.path.exists(caminho_foto_local):
                    caminho_story = os.path.join(PASTA_STORIES, f"story_radar_{post_id.replace('/', '_')}.png")
                    print(f"   🎨 Gerando Story 9:16 com a Logo Oficial...")
                    criar_story_9_16(
                        caminho_foto_produto=caminho_foto_local,
                        titulo=titulo,
                        preco=preco,
                        preco_antigo="",
                        cupom=beneficio,
                        caminho_saida=caminho_story
                    )
                    
                # Formata Legenda para Telegram
                legenda = (
                    f"🛍️ <b>{titulo}</b>\n\n"
                    f"💰 <b>Por apenas: R$ {preco}</b>\n"
                    f"🚚 <b>Benefício:</b> {beneficio}\n"
                    f"📡 <b>Radar:</b> @{canal}\n\n"
                    f"🔗 <b>Link Promocional (Toque e Copie):</b>\n{link_afiliado_usuario}"
                )
                
                # Dispara no Telegram
                if caminho_story and os.path.exists(caminho_story):
                    res_tg = enviar_para_telegram(caminho_story, legenda)
                    print(f"   📲 Enviado para o Telegram: {res_tg}")
                
                # Marca como visto
                vistos.add(post_id)
                novas_ofertas.append({
                    "post_id": post_id,
                    "canal": canal,
                    "titulo": titulo,
                    "preco": preco,
                    "cupom": cupom,
                    "link_afiliado": link_afiliado_usuario,
                    "caminho_story": caminho_story,
                    "timestamp": int(time.time())
                })
                
                time.sleep(2)
                
        except Exception as e:
            print(f"   ⚠️ Erro ao verificar @{canal}: {e}")
            
    salvar_vistos(vistos)
    print(f"✅ [RADAR] Varredura concluída. Novas ofertas processadas: {len(novas_ofertas)}")
    return novas_ofertas

if __name__ == "__main__":
    varrer_canais()
