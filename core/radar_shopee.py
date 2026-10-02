import os
import sys
import re
import json
import time
import requests
import gc
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.story_generator import criar_story_9_16
from core.telegram_sender import enviar_para_telegram
from core.whatsapp_baileys_sender import enviar_para_grupo_whatsapp, verificar_conexao_baileys

PASTA_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PASTA_MIDIA = os.path.join(PASTA_BASE, "midia")
PASTA_STORIES = os.path.join(PASTA_BASE, "stories_instagram")
ARQUIVO_VISTOS = os.path.join(PASTA_BASE, "config", "vistos_radar.json")

os.makedirs(PASTA_MIDIA, exist_ok=True)
os.makedirs(PASTA_STORIES, exist_ok=True)
os.makedirs(os.path.dirname(ARQUIVO_VISTOS), exist_ok=True)

def limpar_arquivos_temporarios(caminhos: list):
    """Apaga imagens do disco e força o coletor de lixo da memória RAM"""
    for c in caminhos:
        if c and os.path.exists(c):
            try:
                os.remove(c)
            except Exception:
                pass
    gc.collect()

def faxina_pastas_temporarias():
    """Varre e apaga qualquer sobra de mídia antiga para garantir zero consumo de disco e RAM"""
    agora = time.time()
    for pasta in [PASTA_MIDIA, PASTA_STORIES]:
        if os.path.exists(pasta):
            for nome in os.listdir(pasta):
                caminho = os.path.join(pasta, nome)
                if os.path.isfile(caminho):
                    try:
                        # Apaga arquivos com mais de 3 minutos
                        if agora - os.path.getmtime(caminho) > 180:
                            os.remove(caminho)
                    except Exception:
                        pass
    gc.collect()

# Os 5 Canais de Ouro Monitorados
CANAIS_RADAR = [
    "shopeebrcupom",         # Cupons oficiais, R$ 15/R$ 50 OFF e frete grátis
    "casaricadeoracao",      # Achadinhos para casa e cozinha
    "escolhasegura",         # Eletrônicos, gadgets e utilidades
    "Automa_Web_Ofertas_01", # Ofertas variadas e tecnologia
    "ofertasgamerandre"      # Acessórios, fones e setup
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
            json.dump(list(vistos)[-250:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar vistos: {e}")

def converter_link_shopee(link_curto: str) -> str:
    """Expande o link de afiliado da Shopee e injeta o ID de afiliado exclusivo do usuário"""
    try:
        resp = requests.get(link_curto, headers=HEADERS, allow_redirects=True, timeout=12)
        url_destino = resp.url
        
        parsed = urlparse(url_destino)
        query = parse_qs(parsed.query)
        
        query["mmp_pid"] = [AFFILIATE_PID]
        query["utm_source"] = [AFFILIATE_PID]
        query["utm_medium"] = ["affiliates"]
        query["utm_campaign"] = ["radar_achadinhos"]
        
        nova_query = urlencode(query, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, nova_query, parsed.fragment))
    except Exception:
        sep = "&" if "?" in link_curto else "?"
        return f"{link_curto}{sep}mmp_pid={AFFILIATE_PID}&utm_source={AFFILIATE_PID}&utm_medium=affiliates"

def varrer_canais() -> list:
    """Varre todos os 5 canais do Telegram, identifica Cupons e Ofertas, troca links e dispara"""
    faxina_pastas_temporarias()
    vistos = carregar_vistos()
    novos_processados = []
    
    print("\n📡 [RADAR] Iniciando varredura contínua nos 5 canais da Shopee...")
    
    # Verifica se o WhatsApp está pronto para envio
    status_wpp = verificar_conexao_baileys()
    wpp_conectado = status_wpp.get("conectado", False)
    
    for canal in CANAIS_RADAR:
        url_canal = f"https://t.me/s/{canal}"
        try:
            r = requests.get(url_canal, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
                
            html = r.text
            
            # Encontra blocos de mensagens com ID único
            blocos = re.findall(r'<div class="tgme_widget_message_wrap[^"]*"[^>]*data-post="([^"]+)"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
            if not blocos:
                posts = re.findall(r'data-post="([^"]+)"', html)
                blocos = [(p, html) for p in posts[-15:]]
                
            for post_id, conteudo in blocos[-8:]:
                if post_id in vistos:
                    continue
                    
                # Procura links da Shopee na mensagem
                shopee_links = re.findall(r'https://s\.shopee\.com\.br/[a-zA-Z0-9]+', conteudo) + re.findall(r'https://shopee\.com\.br/[^\s"\'<>]+', conteudo)
                if not shopee_links:
                    continue
                    
                link_concorrente = shopee_links[0]
                
                # Extrai texto limpo
                m_text = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', conteudo, re.DOTALL)
                texto_bruto = m_text.group(1) if m_text else conteudo
                texto_limpo = re.sub(r'<[^>]+>', ' ', texto_bruto)
                texto_limpo = " ".join(texto_limpo.split())
                
                # ----------------------------------------------------
                # IDENTIFICAÇÃO: É CUPOM OU OFERTA DE PRODUTO?
                # ----------------------------------------------------
                e_cupom = bool(
                    "cupom" in texto_limpo.lower() or 
                    "off em" in texto_limpo.lower() or 
                    "resgate aqui" in texto_limpo.lower() or 
                    canal == "shopeebrcupom"
                )
                
                # Converte o link para o código do usuário
                link_afiliado_usuario = converter_link_shopee(link_concorrente)
                
                # Extrai foto do post do Telegram se houver
                m_foto = re.search(r"background-image:url\('([^']+)'\)", conteudo)
                foto_url = m_foto.group(1) if m_foto else ""
                if not foto_url or "emoji" in foto_url:
                    cdn_matches = [u for u in re.findall(r'https://cdn\d*\.telesco\.pe/file/[^\s"\')]+\.jpg', conteudo) if 'emoji' not in u]
                    if cdn_matches:
                        foto_url = cdn_matches[0]
                        
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

                # ----------------------------------------------------
                # CASO 1: É UM CUPOM RELÂMPAGO
                # ----------------------------------------------------
                if e_cupom:
                    # Extrai código do cupom (ex: C0RR1D41010)
                    m_cod = re.search(r'(?:Cupom|CUPOM):\s*([A-Za-z0-9_-]+)', texto_limpo)
                    codigo_cupom = m_cod.group(1).strip() if m_cod else "VERIFIQUE_NO_LINK"
                    
                    # Extrai regra do desconto (ex: R$ 15,00 OFF em R$ 89,00)
                    m_desc = re.search(r'(R\$\s*[\d.,]+\s*OFF[^\n.!?]*)', texto_limpo, re.IGNORECASE)
                    regra_desconto = m_desc.group(1).strip() if m_desc else "Desconto Especial Liberado!"
                    
                    print(f"\n🎟️ [CUPOM NOVO DETECTADO @{canal}]: {regra_desconto} | Código: {codigo_cupom}")
                    
                    # Legenda para Telegram
                    legenda_tg = (
                        f"🚨 <b>CUPOM RELÂMPAGO SHOPEE!</b> 🎟️\n\n"
                        f"🏷️ <b>Desconto:</b> {regra_desconto}\n"
                        f"🔑 <b>Código:</b> <code>{codigo_cupom}</code> <i>(Toque para copiar)</i>\n"
                        f"📡 <b>Radar:</b> @{canal}\n\n"
                        f"🛒 <b>Resgate o Cupom Antes que Esgote:</b>\n{link_afiliado_usuario}\n\n"
                        f"⚠️ <i>Cupons Shopee possuem limite de uso, corra!</i>"
                    )
                    
                    # Legenda para WhatsApp
                    legenda_wpp = (
                        f"🚨 *CUPOM RELÂMPAGO SHOPEE!* 🎟️\n\n"
                        f"🏷️ *Desconto:* {regra_desconto}\n"
                        f"🔑 *Código:* `{codigo_cupom}`\n\n"
                        f"🛒 *Resgate o cupom antes que esgote:*\n{link_afiliado_usuario}\n\n"
                        f"⚠️ *Corra que os cupons acabam rápido!*"
                    )
                    
                    # Gera Story com a Logo da Família se houver imagem ou usa template
                    caminho_story = ""
                    if caminho_foto_local and os.path.exists(caminho_foto_local):
                        caminho_story = os.path.join(PASTA_STORIES, f"story_cupom_{post_id.replace('/', '_')}.png")
                        criar_story_9_16(
                            caminho_foto_produto=caminho_foto_local,
                            titulo=f"CUPOM {regra_desconto}",
                            preco=codigo_cupom,
                            preco_antigo="",
                            cupom="Ative no App da Shopee",
                            caminho_saida=caminho_story
                        )
                        
                    # Dispara no Telegram
                    if caminho_story and os.path.exists(caminho_story):
                        enviar_para_telegram(caminho_story, legenda_tg)
                    
                    # Dispara no WhatsApp se conectado
                    if wpp_conectado:
                        enviar_para_grupo_whatsapp(caminho_foto_local, legenda_wpp)
                        print(f"   📲 Cupom enviado ao Grupo do WhatsApp!")

                    # Limpa arquivos imediatamente para liberar disco e memória RAM
                    limpar_arquivos_temporarios([caminho_foto_local, caminho_story])

                # ----------------------------------------------------
                # CASO 2: É UMA OFERTA DE PRODUTO
                # ----------------------------------------------------
                else:
                    primeira_linha = texto_limpo.split("POR:")[0].split("DE:")[0].split("R$")[0].strip()
                    titulo = re.sub(r'^[^\w\s]+', '', primeira_linha).strip()
                    if len(titulo) > 55:
                        titulo = titulo[:55].rsplit(" ", 1)[0]
                    if len(titulo) < 5:
                        titulo = "Achadinho Especial Shopee"
                        
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
                        
                    print(f"\n🛍️ [PRODUTO NOVO DETECTADO @{canal}]: {titulo} (R$ {preco})")
                    
                    caminho_story = ""
                    if caminho_foto_local and os.path.exists(caminho_foto_local):
                        caminho_story = os.path.join(PASTA_STORIES, f"story_radar_{post_id.replace('/', '_')}.png")
                        criar_story_9_16(
                            caminho_foto_produto=caminho_foto_local,
                            titulo=titulo,
                            preco=preco,
                            preco_antigo="",
                            cupom="Cupom de Frete no App",
                            caminho_saida=caminho_story
                        )
                        
                    legenda_tg = (
                        f"🛍️ <b>{titulo}</b>\n\n"
                        f"💰 <b>Por apenas: R$ {preco}</b>\n"
                        f"🚚 <b>Benefício:</b> Frete Grátis com Cupom\n"
                        f"📡 <b>Radar:</b> @{canal}\n\n"
                        f"🔗 <b>Link Promocional (Toque e Copie):</b>\n{link_afiliado_usuario}"
                    )
                    
                    legenda_wpp = (
                        f"🛍️ *{titulo}*\n\n"
                        f"💰 *Por apenas: R$ {preco}*\n"
                        f"🚚 *Benefício:* Cupom de Frete no App\n\n"
                        f"🛒 *Compre com segurança aqui:*\n{link_afiliado_usuario}\n\n"
                        f"⚠️ *Oferta por tempo limitado!*"
                    )
                    
                    # Dispara no Telegram
                    if caminho_story and os.path.exists(caminho_story):
                        enviar_para_telegram(caminho_story, legenda_tg)
                        
                    # Dispara no WhatsApp se conectado
                    if wpp_conectado:
                        enviar_para_grupo_whatsapp(caminho_foto_local, legenda_wpp)
                        print(f"   📲 Oferta enviada ao Grupo do WhatsApp!")

                    # Limpa arquivos imediatamente para liberar disco e memória RAM
                    limpar_arquivos_temporarios([caminho_foto_local, caminho_story])

                vistos.add(post_id)
                novos_processados.append({
                    "post_id": post_id,
                    "canal": canal,
                    "tipo": "cupom" if e_cupom else "produto",
                    "timestamp": int(time.time())
                })
                time.sleep(2)
                
        except Exception as e:
            print(f"   ⚠️ Erro ao verificar @{canal}: {e}")
            
    salvar_vistos(vistos)
    print(f"✅ [RADAR] Varredura concluída. Novos itens processados: {len(novos_processados)}")
    return novos_processados

if __name__ == "__main__":
    varrer_canais()
