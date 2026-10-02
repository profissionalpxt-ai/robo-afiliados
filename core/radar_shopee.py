import os
import sys
import re
import json
import time
import requests
import gc
import html
from bs4 import BeautifulSoup
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
ARQUIVO_HISTORICO = os.path.join(PASTA_BASE, "config", "historico_envios.json")
ARQUIVO_STATUS = os.path.join(PASTA_BASE, "config", "status_radar.json")
ARQUIVO_FILA = os.path.join(PASTA_BASE, "fila", "ofertas_prontas.json")

os.makedirs(PASTA_MIDIA, exist_ok=True)
os.makedirs(PASTA_STORIES, exist_ok=True)
os.makedirs(os.path.dirname(ARQUIVO_VISTOS), exist_ok=True)

def carregar_status_radar() -> dict:
    if os.path.exists(ARQUIVO_STATUS):
        try:
            with open(ARQUIVO_STATUS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"envios_ativos": True}

def salvar_status_radar(status_dict: dict):
    try:
        atual = carregar_status_radar()
        atual.update(status_dict)
        with open(ARQUIVO_STATUS, "w", encoding="utf-8") as f:
            json.dump(atual, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar status do radar: {e}")

def registrar_log_envio(tipo: str, titulo: str, canal: str, wpp_status: str, tg_status: str, link: str):
    """Registra cada disparo no histórico leve de logs (mantém apenas os últimos 50 itens)"""
    try:
        historico = []
        if os.path.exists(ARQUIVO_HISTORICO):
            try:
                with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                    historico = json.load(f)
            except Exception:
                historico = []

        import datetime
        agora_str = datetime.datetime.now().strftime("%d/%m %H:%M:%S")

        novo = {
            "hora": agora_str,
            "timestamp": int(time.time()),
            "tipo": tipo,
            "titulo": titulo,
            "canal": f"@{canal}" if not canal.startswith("@") else canal,
            "wpp": wpp_status,
            "tg": tg_status,
            "link": link
        }
        historico.insert(0, novo)
        historico = historico[:50]

        with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar log de histórico: {e}")

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
    """Expande o link da Shopee, remove o lixo criptográfico e gera link limpo de 1 linha"""
    try:
        resp = requests.get(link_curto, headers=HEADERS, allow_redirects=True, timeout=12)
        url_destino = resp.url
        
        # Procura Shop ID e Item ID para montar a URL curta direta
        m = re.search(r'/(\d{6,})[/?&]?.*?(\d{8,})', url_destino)
        if m:
            shop_id, item_id = m.group(1), m.group(2)
            return f"https://shopee.com.br/product/{shop_id}/{item_id}?mmp_pid={AFFILIATE_PID}&utm_source={AFFILIATE_PID}&utm_medium=affiliates"
            
        # Caso seja página de cupons ou outra categoria
        parsed = urlparse(url_destino)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?mmp_pid={AFFILIATE_PID}&utm_source={AFFILIATE_PID}&utm_medium=affiliates"
    except Exception:
        sep = "&" if "?" in link_curto else "?"
        return f"{link_curto}{sep}mmp_pid={AFFILIATE_PID}&utm_source={AFFILIATE_PID}&utm_medium=affiliates"

def varrer_canais() -> list:
    """Varre todos os 5 canais do Telegram, identifica Cupons e Ofertas, troca links e dispara"""
    faxina_pastas_temporarias()
    status_radar = carregar_status_radar()
    if not status_radar.get("envios_ativos", True):
        print("⏸️ [RADAR] Envios pausados no momento pelo usuário no painel.")
        return []

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
                
            soup = BeautifulSoup(r.text, 'html.parser')
            msgs = soup.find_all('div', class_=re.compile(r'tgme_widget_message\b'))
            
            for msg in msgs[-10:]:
                post_id = msg.get('data-post', '')
                if not post_id or post_id in vistos:
                    continue
                    
                # Procura links da Shopee especificamente nesta mensagem
                shopee_links = re.findall(r'https://s\.shopee\.com\.br/[a-zA-Z0-9]+', str(msg)) + re.findall(r'https://shopee\.com\.br/[^\s"\'<>]+', str(msg))
                if not shopee_links:
                    continue
                    
                link_concorrente = shopee_links[0]
                
                # Extrai texto limpo
                div_text = msg.find(class_=re.compile(r'tgme_widget_message_text'))
                texto_limpo = div_text.get_text(separator=' ').strip() if div_text else ""
                texto_limpo = html.unescape(texto_limpo)
                texto_limpo = " ".join(texto_limpo.split())
                
                # Identifica se tem preço de produto
                m_preco = re.search(r'(?:POR|Por apenas|Preço):\s*(?:R\$\s*)?([\d.,]+)', texto_limpo, re.IGNORECASE)
                if not m_preco:
                    m_preco = re.search(r'R\$\s*([\d.,]+)', texto_limpo)
                tem_preco = bool(m_preco)

                # É cupom se não tiver preço e mencionar cupom
                e_cupom = bool(
                    (canal == "shopeebrcupom" or "código" in texto_limpo.lower() or "cupom:" in texto_limpo.lower()) 
                    and not tem_preco
                )
                
                # Converte o link para o código do usuário (link curto e limpo)
                link_afiliado_usuario = converter_link_shopee(link_concorrente)
                
                # Extrai foto do produto na mensagem (ignora fotos de perfil)
                foto_div = msg.find(class_=re.compile(r'tgme_widget_message_photo_wrap'))
                foto_url = ""
                if foto_div and 'style' in foto_div.attrs:
                    m_img = re.search(r"background-image:url\('([^']+)'\)", foto_div['style'])
                    if m_img:
                        foto_url = m_img.group(1)
                
                caminho_foto_local = ""
                if foto_url and foto_url.startswith("http") and "emoji" not in foto_url:
                    try:
                        r_foto = requests.get(foto_url, timeout=15)
                        if len(r_foto.content) > 5000:
                            caminho_foto_local = os.path.join(PASTA_MIDIA, f"radar_{post_id.replace('/', '_')}.jpg")
                            with open(caminho_foto_local, "wb") as f_img:
                                f_img.write(r_foto.content)
                    except Exception as e:
                        print(f"   ⚠️ Falha ao baixar foto: {e}")

                # ----------------------------------------------------
                # CASO 1: CUPOM RELÂMPAGO
                # ----------------------------------------------------
                if e_cupom:
                    m_cod = re.search(r'(?:Cupom|CUPOM):\s*([A-Za-z0-9_-]+)', texto_limpo)
                    codigo_cupom = m_cod.group(1).strip() if m_cod else "VERIFIQUE_NO_LINK"
                    
                    m_desc = re.search(r'(R\$\s*[\d.,]+\s*OFF[^\n.!?]*)', texto_limpo, re.IGNORECASE)
                    regra_desconto = m_desc.group(1).strip() if m_desc else "Desconto Especial Liberado!"
                    
                    print(f"\n🎟️ [CUPOM NOVO DETECTADO @{canal}]: {regra_desconto} | Código: {codigo_cupom}")
                    
                    legenda_tg = (
                        f"🚨 <b>CUPOM RELÂMPAGO SHOPEE!</b> 🎟️\n\n"
                        f"🏷️ <b>Desconto:</b> {regra_desconto}\n"
                        f"🔑 <b>Código:</b> <code>{codigo_cupom}</code> <i>(Toque para copiar)</i>\n"
                        f"📡 <b>Radar:</b> @{canal}\n\n"
                        f"🛒 <b>Resgate o Cupom Antes que Esgote:</b>\n{link_afiliado_usuario}\n\n"
                        f"⚠️ <i>Cupons Shopee possuem limite de uso, corra!</i>"
                    )
                    
                    legenda_wpp = (
                        f"🚨 *CUPOM RELÂMPAGO SHOPEE!* 🎟️\n\n"
                        f"🏷️ *Desconto:* {regra_desconto}\n"
                        f"🔑 *Código:* `{codigo_cupom}`\n\n"
                        f"🛒 *Resgate o cupom antes que esgote:*\n{link_afiliado_usuario}\n\n"
                        f"⚠️ *Corra que os cupons acabam rápido!*"
                    )
                    
                    caminho_story = os.path.join(PASTA_STORIES, f"story_cupom_{post_id.replace('/', '_')}.png")
                    criar_story_9_16(
                        caminho_foto_produto=caminho_foto_local,
                        titulo=f"CUPOM {regra_desconto}",
                        preco=codigo_cupom,
                        preco_antigo="",
                        cupom="Ative no App da Shopee",
                        caminho_saida=caminho_story
                    )
                        
                    if os.path.exists(caminho_story):
                        enviar_para_telegram(caminho_story, legenda_tg)
                    
                    w_st = "Pendente"
                    if wpp_conectado:
                        foto_envio = caminho_foto_local if os.path.exists(caminho_foto_local) else caminho_story
                        enviar_para_grupo_whatsapp(foto_envio, legenda_wpp)
                        w_st = "Enviado"
                        print(f"   📲 Cupom enviado ao Grupo do WhatsApp!")

                    registrar_log_envio(
                        tipo="CUPOM",
                        titulo=f"CUPOM {regra_desconto} ({codigo_cupom})",
                        canal=canal,
                        wpp_status=w_st,
                        tg_status="Enviado",
                        link=link_afiliado_usuario
                    )

                    limpar_arquivos_temporarios([caminho_foto_local, caminho_story])

                # ----------------------------------------------------
                # CASO 2: OFERTA DE PRODUTO
                # ----------------------------------------------------
                else:
                    primeira_linha = texto_limpo.split("POR:")[0].split("Por apenas")[0].split("De:")[0].split("R$")[0].strip()
                    titulo = re.sub(r'^[^\w\s]+', '', primeira_linha).strip()
                    if len(titulo) > 55:
                        titulo = titulo[:55].rsplit(" ", 1)[0]
                    if len(titulo) < 5:
                        titulo = "Achadinho Especial Shopee"
                        
                    if m_preco:
                        preco_num = m_preco.group(1).replace(".", "").replace(",", ".")
                        try:
                            preco = f"{float(preco_num):.2f}".replace(".", ",")
                        except Exception:
                            preco = m_preco.group(1)
                    else:
                        preco = "Confira no Link"
                        
                    print(f"\n🛍️ [PRODUTO NOVO DETECTADO @{canal}]: {titulo} (R$ {preco})")
                    
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
                    
                    if os.path.exists(caminho_story):
                        enviar_para_telegram(caminho_story, legenda_tg)
                        
                    w_st = "Pendente"
                    if wpp_conectado:
                        foto_envio = caminho_foto_local if os.path.exists(caminho_foto_local) else caminho_story
                        enviar_para_grupo_whatsapp(foto_envio, legenda_wpp)
                        w_st = "Enviado"
                        print(f"   📲 Oferta enviada ao Grupo do WhatsApp!")

                    registrar_log_envio(
                        tipo="PRODUTO",
                        titulo=f"{titulo} (R$ {preco})",
                        canal=canal,
                        wpp_status=w_st,
                        tg_status="Enviado",
                        link=link_afiliado_usuario
                    )

                    if foto_url and tem_preco:
                        salvar_oferta_na_fila({
                            "titulo": titulo,
                            "preco": preco,
                            "link_afiliado": link_afiliado_usuario,
                            "foto_url": foto_url,
                            "canal": canal
                        })

                    limpar_arquivos_temporarios([caminho_foto_local, caminho_story])

                vistos.add(post_id)
                novos_processados.append({
                    "post_id": post_id,
                    "canal": canal,
                    "tipo": "cupom" if e_cupom else "produto",
                    "timestamp": int(time.time())
                })
                # Processa 1 item por ciclo para manter cadência perfeita
                break
                
            if novos_processados:
                break
                
        except Exception as e:
            print(f"   ⚠️ Erro ao verificar @{canal}: {e}")
            
    salvar_vistos(vistos)
    print(f"✅ [RADAR] Varredura concluída. Novos itens processados: {len(novos_processados)}")

    # Conta quantas ofertas restam na fila de reserva
    total_fila = 0
    if os.path.exists(ARQUIVO_FILA):
        try:
            with open(ARQUIVO_FILA, "r", encoding="utf-8") as f_q:
                total_fila = len(json.load(f_q))
        except Exception:
            pass

    # Se nenhum canal postou nada novo, dispara imediatamente da fila de reserva!
    if len(novos_processados) == 0 and total_fila > 0:
        print("📦 [FILA RESERVA] Canais sem novidades neste ciclo. Disparando 1 item da fila com foto...")
        disparar_item_fila_reserva(wpp_conectado)

    # Cadência dinâmica: 180s (3 min) se fila > 10; 300s (5 min) se <= 10
    intervalo_segundos = 180 if total_fila > 10 else 300

    import datetime
    salvar_status_radar({
        "ultima_varredura": datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
        "status": "online",
        "envios_ativos": status_radar.get("envios_ativos", True),
        "canais_ativos": len(CANAIS_RADAR),
        "total_fila_reserva": total_fila,
        "novos_ultimo_ciclo": len(novos_processados),
        "proxima_varredura_segundos": intervalo_segundos
    })

    return novos_processados

def salvar_oferta_na_fila(item_dict: dict):
    try:
        fila = []
        if os.path.exists(ARQUIVO_FILA):
            try:
                with open(ARQUIVO_FILA, "r", encoding="utf-8") as f:
                    fila = json.load(f)
            except Exception:
                fila = []
        if not any(x.get("link_afiliado") == item_dict.get("link_afiliado") for x in fila):
            fila.append(item_dict)
            fila = fila[-50:]
            with open(ARQUIVO_FILA, "w", encoding="utf-8") as f:
                json.dump(fila, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar na fila: {e}")

def disparar_item_fila_reserva(wpp_conectado: bool):
    """Dispara um item da fila de reserva com foto real e preço exato"""
    if not os.path.exists(ARQUIVO_FILA):
        return
    try:
        with open(ARQUIVO_FILA, "r", encoding="utf-8") as f:
            fila = json.load(f)
        if not fila:
            return
            
        item = fila.pop(0)
        fila.append(item) # Rotação contínua
        with open(ARQUIVO_FILA, "w", encoding="utf-8") as f:
            json.dump(fila, f, indent=2, ensure_ascii=False)
            
        titulo = item.get("titulo", "Achadinho Especial da Família")
        preco = item.get("preco", "Oferta")
        preco_antigo = item.get("preco_antigo", "")
        cupom = item.get("cupom", "Cupom de Frete no App")
        condicao = item.get("condicao", "")
        link = item.get("link_afiliado", "")
        link_usuario = converter_link_shopee(link)
        
        # Se tiver foto_url na nuvem, baixa para enviar foto real
        foto_url = item.get("foto_url", "")
        caminho_foto_local = item.get("caminho_imagem", "")
        if not (caminho_foto_local and os.path.exists(caminho_foto_local)) and foto_url:
            try:
                r_f = requests.get(foto_url, timeout=15)
                if len(r_f.content) > 5000:
                    caminho_foto_local = os.path.join(PASTA_MIDIA, f"reserva_{int(time.time())}.jpg")
                    with open(caminho_foto_local, "wb") as f_img:
                        f_img.write(r_f.content)
            except Exception:
                caminho_foto_local = ""
                
        # Gera Story Oficial 9:16 com a Logo da Família
        caminho_story = os.path.join(PASTA_STORIES, f"story_reserva_{int(time.time())}.png")
        criar_story_9_16(
            caminho_foto_produto=caminho_foto_local if (caminho_foto_local and os.path.exists(caminho_foto_local)) else "",
            titulo=titulo,
            preco=preco,
            preco_antigo=preco_antigo,
            cupom=cupom,
            condicao=condicao,
            caminho_saida=caminho_story
        )
        
        foto_envio = caminho_foto_local if (caminho_foto_local and os.path.exists(caminho_foto_local)) else (caminho_story if os.path.exists(caminho_story) else "")
        
        legenda_wpp = (
            f"🛍️ *{titulo}*\n\n"
            f"💰 *Por apenas: R$ {preco}*\n"
            f"🚚 *Benefício:* Cupom de Frete no App\n\n"
            f"🛒 *Compre com segurança aqui:*\n{link_usuario}\n\n"
            f"⚠️ *Oferta por tempo limitado!*"
        )
        legenda_tg = (
            f"🛍️ <b>{titulo}</b>\n\n"
            f"💰 <b>Por apenas: R$ {preco}</b>\n"
            f"🚚 <b>Benefício:</b> Frete Grátis com Cupom\n"
            f"📡 <b>Radar:</b> Fila de Reserva\n\n"
            f"🔗 <b>Link Promocional:</b>\n{link_usuario}"
        )
        
        if foto_envio:
            enviar_para_telegram(foto_envio, legenda_tg)
        else:
            enviar_para_telegram("", legenda_tg)
        
        w_st = "Pendente"
        if wpp_conectado:
            enviar_para_grupo_whatsapp(foto_envio, legenda_wpp)
            w_st = "Enviado"
            
        registrar_log_envio(
            tipo="PRODUTO",
            titulo=f"{titulo} (R$ {preco})",
            canal="@Fila_Reserva",
            wpp_status=w_st,
            tg_status="Enviado",
            link=link_usuario
        )
        print(f"📦 [FILA RESERVA] Oferta postada com foto real: {titulo}")
        
        limpar_arquivos_temporarios([caminho_foto_local, caminho_story])
    except Exception as e:
        print(f"Erro ao disparar item da fila reserva: {e}")

if __name__ == "__main__":
    varrer_canais()
