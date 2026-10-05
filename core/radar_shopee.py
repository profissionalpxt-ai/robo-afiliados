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

# Canais Ativos Monitorados (PRODUTOS COM FOTO NO TOPO, CUPOM EM ÚLTIMO)
CANAIS_RADAR = [
    "casaricadeoracao",      # Achadinhos para casa e cozinha (MUITOS PRODUTOS COM FOTO - ATIVO HOJE)
    "escolhasegura",         # Eletrônicos, gadgets e utilidades (MUITOS PRODUTOS COM FOTO - ATIVO HOJE)
    "shopeebrcupom"          # Cupons oficiais (APENAS EM ÚLTIMO CASO SE NÃO HOUVER PRODUTO)
]

AFFILIATE_PID = "an_18316781247"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def limpar_linhas_espelhadas_emojis(texto: str) -> str:
    """Corrige textos onde os emojis foram separados em linhas isoladas, unindo-os ao texto"""
    if not texto:
        return ""
    linhas = [l.strip() for l in texto.split('\n')]
    linhas_limpas = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha:
            if linhas_limpas and linhas_limpas[-1] != "":
                linhas_limpas.append("")
            i += 1
            continue
        # Se a linha contiver APENAS emojis ou símbolos gráficos (sem letras/números)
        if re.match(r'^[^\w\s\d]+$', linha):
            j = i + 1
            while j < len(linhas) and not linhas[j]:
                j += 1
            if j < len(linhas) and linhas[j]:
                linhas_limpas.append(f"{linha} {linhas[j]}")
                i = j + 1
                continue
            else:
                linhas_limpas.append(linha)
                i += 1
                continue
        else:
            linhas_limpas.append(linha)
            i += 1
    res = '\n'.join(linhas_limpas).strip()
    return re.sub(r'\n{3,}', '\n\n', res)

def formatar_html_telegram_para_whatsapp(tag) -> str:
    """Converte o HTML da mensagem do Telegram mantendo emojis na mesma linha,
    convertendo negrito para asteriscos do WhatsApp e respeitando a diagramação original."""
    if not tag:
        return ""
    raw = ''.join(str(c) for c in tag.contents)
    raw = re.sub(r'<br\s*/?>', '\n', raw, flags=re.IGNORECASE)
    raw = re.sub(r'</p\s*>', '\n', raw, flags=re.IGNORECASE)
    raw = re.sub(r'<b\b[^>]*>(.*?)</b>', r'*\1*', raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r'<strong\b[^>]*>(.*?)</strong>', r'*\1*', raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r'<[^>]+>', '', raw)
    # Remove asteriscos redundantes ao redor de emojis
    raw = re.sub(r'\*([^\w\s\d]+)\*', r'\1', raw)
    texto = html.unescape(raw)
    return limpar_linhas_espelhadas_emojis(texto)

def extrair_titulo_produto(texto: str) -> str:
    """Extrai com precisão cirúrgica o nome real do produto sem emojis ou tags"""
    for linha in texto.split('\n'):
        linha = linha.strip()
        if not linha:
            continue
        # Remove emojis, asteriscos e pontuação do início para análise limpa
        linha_limpa = re.sub(r'^[^\w\s]+', '', linha).replace('*', '').strip()
        if not linha_limpa:
            continue
        # Ignora palavras de cabeçalho ou tags promocionais
        if any(linha_limpa.lower().startswith(x) for x in ['achadinho', 'confira', 'cupom', 'de:', 'por:', 'use o', 'resgate', 'link', 'compre', '#', 'oferta', 'alerta', 'total']):
            continue
        if len(linha_limpa) >= 5:
            return linha_limpa[:55]
    return "Achadinho da Família"

def extrair_codigo_cupom(texto: str) -> str:
    """Extrai código de cupom promocional para alertar no texto fora da foto"""
    stopwords = {'de', 'no', 'na', 'do', 'da', 'para', 'em', 'frete', 'desconto', 'app', 'pagina', 'loja', 'aqui', 'shopee'}
    m = re.search(r'(?:use\s+o\s+cupom|com\s+o\s+cupom|aplique\s+o\s+cupom|cupom):?\s*([A-Za-z0-9_-]{3,})', texto, re.IGNORECASE)
    if m:
        c = m.group(1).strip()
        if c.lower() not in stopwords:
            return c.upper()
    return ""

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

def converter_link_mercadolivre(link: str) -> str:
    """Converte links do Mercado Livre para o ID de afiliado do Cássio (pai do usuário)"""
    try:
        resp = requests.get(link, headers=HEADERS, allow_redirects=True, timeout=12)
        url_dest = resp.url
        if 'go=' in url_dest:
            from urllib.parse import unquote
            m = url_dest.split('go=')[1].split('&')[0]
            url_dest = unquote(m)
            
        parsed = urlparse(url_dest)
        qs = parse_qs(parsed.query)
        qs['matt_tool'] = ['54058478']
        qs['matt_word'] = ['cassiopeixotomacedo']
        qs['forceInApp'] = ['true']
        
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', urlencode(qs, doseq=True), ''))
    except Exception:
        sep = "&" if "?" in link else "?"
        return f"{link}{sep}matt_tool=54058478&matt_word=cassiopeixotomacedo&forceInApp=true"

def varrer_canais() -> list:
    """Varre todos os 5 canais, mantém o texto e foto originais e apenas substitui o link pelo de afiliado"""
    faxina_pastas_temporarias()
    status_radar = carregar_status_radar()
    if not status_radar.get("envios_ativos", True):
        print("⏸️ [RADAR] Envios pausados no momento pelo usuário no painel.")
        return []

    vistos = carregar_vistos()
    novos_processados = []
    
    print("\n📡 [RADAR] Iniciando varredura contínua nos 5 canais (Shopee + Mercado Livre)...")
    
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
            
            for msg in msgs[-15:]:
                post_id = msg.get('data-post', '')
                if not post_id or post_id in vistos:
                    continue
                    
                # Procura links da Shopee e do Mercado Livre na mensagem
                shopee_links = re.findall(r'https://s\.shopee\.com\.br/[a-zA-Z0-9]+', str(msg)) + re.findall(r'https://shopee\.com\.br/[^\s"\'<>]+', str(msg))
                meli_links = re.findall(r'https://meli\.la/[a-zA-Z0-9]+', str(msg)) + re.findall(r'https://(?:www\.)?mercadolivre\.com\.br/[^\s"\'<>]+', str(msg))
                
                if not shopee_links and not meli_links:
                    continue
                    
                # Extrai o texto ORIGINAL completo da mensagem
                div_text = msg.find(class_=re.compile(r'tgme_widget_message_text'))
                if not div_text:
                    continue
                    
                # Extrai o texto da mensagem mantendo layout idêntico e emojis na mesma linha
                texto_original = formatar_html_telegram_para_whatsapp(div_text)
                
                # Substitui apenas os links pelos links de afiliado corretos
                texto_final = texto_original
                link_principal = ""
                
                # Shopee -> Afiliado do Usuário (an_18316781247)
                for l_orig in shopee_links:
                    l_novo = converter_link_shopee(l_orig)
                    texto_final = texto_final.replace(l_orig, l_novo)
                    if not link_principal:
                        link_principal = l_novo
                        
                # Mercado Livre -> Afiliado do Cássio (54058478 / cassiopeixotomacedo)
                for l_orig in meli_links:
                    l_novo = converter_link_mercadolivre(l_orig)
                    texto_final = texto_final.replace(l_orig, l_novo)
                    if not link_principal:
                        link_principal = l_novo

                # Extrai a FOTO ORIGINAL exata do produto postado
                foto_div = msg.find(class_=re.compile(r'tgme_widget_message_photo_wrap'))
                foto_url = ""
                if foto_div and 'style' in foto_div.attrs:
                    m_img = re.search(r"background-image:url\('([^']+)'\)", foto_div['style'])
                    if m_img:
                        foto_url = m_img.group(1)
                
                caminho_foto_local = ""
                if foto_url and foto_url.startswith("http") and "emoji" not in foto_url:
                    try:
                        r_foto = requests.get(foto_url, headers=HEADERS, timeout=15)
                        if len(r_foto.content) > 3000:
                            # Valida se os bytes são realmente de uma imagem válida
                            from PIL import Image
                            import io
                            test_img = Image.open(io.BytesIO(r_foto.content))
                            test_img.verify()
                            
                            caminho_foto_local = os.path.join(PASTA_MIDIA, f"radar_{post_id.replace('/', '_')}.jpg")
                            with open(caminho_foto_local, "wb") as f_img:
                                f_img.write(r_foto.content)
                    except Exception as e:
                        print(f"   ⚠️ Falha ao baixar ou validar foto original: {e}")
                        caminho_foto_local = ""

                # Identifica cupom se houver no texto usando regex inteligente
                cupom_extraido = extrair_codigo_cupom(texto_original)
                
                # Se for do canal de cupons sem foto ou sem imagem válida, é aviso de cupom
                tem_foto_valida = bool(caminho_foto_local and os.path.exists(caminho_foto_local))
                e_cupom_puro = (canal == "shopeebrcupom") or (not tem_foto_valida and "cupom" in texto_original.lower())
                
                titulo_log = extrair_titulo_produto(texto_original) if tem_foto_valida else "Cupom Promocional Shopee"
                
                # Destaque claro do cupom no texto (fora da foto) para o usuário saber que precisa ativar
                texto_wpp = texto_final
                if cupom_extraido and "ative o cupom" not in texto_wpp.lower():
                    # Adiciona lembrete destacado no topo da mensagem
                    texto_wpp = f"🎟️ *ATENÇÃO: Ative o cupom {cupom_extraido} no carrinho para obter o menor preço!*\n\n" + texto_wpp

                print(f"\n🚀 [DISPARANDO { 'CUPOM' if e_cupom_puro else 'PRODUTO' } @{canal}]: {titulo_log}")
                
                tg_st = "Ignorado (Cupom)"
                w_st = "Pendente"
                
                if e_cupom_puro:
                    # Envia no WhatsApp apenas o texto oficial do cupom com o link
                    if wpp_conectado:
                        res_w = enviar_para_grupo_whatsapp("", texto_wpp)
                        print(f"👉 RESPOSTA BAILEYS CUPOM: {res_w}")
                        if res_w.get("sucesso") is True:
                            w_st = "Enviado"
                        else:
                            w_st = f"Erro ({res_w.get('erro', 'Falha')})"
                else:
                    # PRODUTO COM FOTO: Gera o Story 9:16 Oficial com a Logo da Família para o Telegram
                    caminho_story_telegram = ""
                    try:
                        m_preco = re.search(r'(?:R\$|POR:?\s*R\$)\s*([\d\.,]+)', texto_original, re.IGNORECASE)
                        preco_extraido = m_preco.group(1) if m_preco else ""
                        m_de = re.search(r'DE:?\s*R\$\s*([\d\.,]+)', texto_original, re.IGNORECASE)
                        preco_de_extraido = m_de.group(1) if m_de else ""

                        caminho_story = os.path.join(PASTA_STORIES, f"story_{post_id.replace('/', '_')}.png")
                        caminho_story_telegram = criar_story_9_16(
                            caminho_foto_produto=caminho_foto_local,
                            titulo=titulo_log,
                            preco=preco_extraido if preco_extraido else "Oferta",
                            preco_antigo=preco_de_extraido,
                            cupom=cupom_extraido,
                            caminho_saida=caminho_story
                        )
                    except Exception as err_story:
                        print(f"   ⚠️ Aviso ao gerar Story 9:16: {err_story}")
                        caminho_story_telegram = caminho_foto_local

                    foto_telegram = caminho_story_telegram if (caminho_story_telegram and os.path.exists(caminho_story_telegram)) else caminho_foto_local
                    res_tg = enviar_para_telegram(foto_telegram, texto_final)
                    tg_st = "Enviado" if res_tg.get("sucesso") else "Erro"

                    # Dispara no WhatsApp: Foto original real do produto + Mensagem com aviso de cupom
                    if wpp_conectado:
                        res_w = enviar_para_grupo_whatsapp(caminho_foto_local, texto_wpp)
                        print(f"👉 RESPOSTA BAILEYS: {res_w}")
                        if res_w.get("sucesso") is True:
                            w_st = "Enviado"
                            print(f"   📲 Oferta enviada ao Grupo do WhatsApp com sucesso!")
                        else:
                            w_st = f"Erro ({res_w.get('erro', 'Falha')})"
                            print(f"   ⚠️ Falha ao enviar para WhatsApp: {res_w}")

                # Registra no log ao vivo
                registrar_log_envio(
                    tipo="CUPOM" if e_cupom_puro else "PRODUTO",
                    titulo=titulo_log,
                    canal=canal,
                    wpp_status=w_st,
                    tg_status="Enviado",
                    link=link_principal
                )

                # Salva na fila de reserva para repetições futuras
                if foto_url:
                    salvar_oferta_na_fila({
                        "titulo": titulo_log,
                        "texto": texto_final,
                        "link_afiliado": link_principal,
                        "foto_url": foto_url,
                        "canal": canal
                    })

                limpar_arquivos_temporarios([caminho_foto_local])

                vistos.add(post_id)
                novos_processados.append({
                    "post_id": post_id,
                    "canal": canal,
                    "tipo": "cupom" if e_cupom_puro else "produto",
                    "timestamp": int(time.time())
                })
                # Processa 1 item por ciclo para respeitar a cadência de 3 a 5 min
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

    # Se nenhum canal postou nada novo, dispara 1 item da fila de reserva!
    if len(novos_processados) == 0 and total_fila > 0:
        print("📦 [FILA RESERVA] Canais sem novidades neste ciclo. Disparando 1 item da fila com foto original...")
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
            fila.insert(0, item_dict)
            fila = fila[:50]
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
                r_f = requests.get(foto_url, headers=HEADERS, timeout=15)
                if len(r_f.content) > 3000:
                    from PIL import Image
                    import io
                    t_img = Image.open(io.BytesIO(r_f.content))
                    t_img.verify()
                    caminho_foto_local = os.path.join(PASTA_MIDIA, f"reserva_{int(time.time())}.jpg")
                    with open(caminho_foto_local, "wb") as f_img:
                        f_img.write(r_f.content)
            except Exception as e:
                print(f"   ⚠️ Imagem da fila de reserva inválida: {e}")
                caminho_foto_local = ""

        texto_envio = item.get("texto", "")
        if not texto_envio:
            texto_envio = (
                f"🛍️ *{titulo}*\n\n"
                f"💰 *Por apenas: R$ {preco}*\n"
                f"🚚 *Benefício:* Cupom de Frete no App\n\n"
                f"🛒 *Compre com segurança aqui:*\n{link_usuario}\n\n"
                f"⚠️ *Oferta por tempo limitado!*"
            )
        else:
            texto_envio = limpar_linhas_espelhadas_emojis(texto_envio)

        # Garante título real e preciso
        if not titulo or titulo in ["Oferta Especial", "Achadinho Especial da Família"]:
            titulo = extrair_titulo_produto(texto_envio)

        # Identifica cupom se houver no texto usando regex inteligente
        cupom_extraido = extrair_codigo_cupom(texto_envio)

        foto_envio_wpp = caminho_foto_local if (caminho_foto_local and os.path.exists(caminho_foto_local)) else ""
        
        # Só é cupom puro se for canal de cupom ou se NÃO tiver foto e falar de cupom
        e_cupom_puro = (item.get("canal") == "shopeebrcupom") or (not foto_envio_wpp and "cupom" in texto_envio.lower())

        # Destaque claro do cupom no texto (fora da foto) para o usuário saber que precisa ativar
        texto_wpp = texto_envio
        if cupom_extraido and "ative o cupom" not in texto_wpp.lower():
            texto_wpp = f"🎟️ *ATENÇÃO: Ative o cupom {cupom_extraido} no carrinho para obter o menor preço!*\n\n" + texto_wpp

        tg_st = "Ignorado (Cupom)"
        w_st = "Pendente"

        if e_cupom_puro:
            # Cupom puro sem foto: apenas texto no WhatsApp, sem foto no Telegram
            if wpp_conectado:
                res_w = enviar_para_grupo_whatsapp("", texto_wpp)
                print(f"👉 RESPOSTA BAILEYS FILA CUPOM: {res_w}")
                if res_w.get("sucesso") is True:
                    w_st = "Enviado"
                else:
                    w_st = f"Erro ({res_w.get('erro', 'Falha')})"
        else:
            # Produto: gera Story Oficial 9:16 com a Logo da Família para o Telegram
            caminho_story = os.path.join(PASTA_STORIES, f"story_reserva_{int(time.time())}.png")
            caminho_story_pronto = criar_story_9_16(
                caminho_foto_produto=caminho_foto_local if (caminho_foto_local and os.path.exists(caminho_foto_local)) else "",
                titulo=titulo,
                preco=preco,
                preco_antigo=preco_antigo,
                cupom=cupom_extraido if cupom_extraido else cupom,
                condicao=condicao,
                caminho_saida=caminho_story
            )
            foto_envio_tg = caminho_story_pronto if (caminho_story_pronto and os.path.exists(caminho_story_pronto)) else foto_envio_wpp
            res_tg = enviar_para_telegram(foto_envio_tg, texto_envio)
            tg_st = "Enviado" if res_tg.get("sucesso") else "Erro"

            # Dispara no WhatsApp: Foto original real do produto + Mensagem com aviso de cupom
            if wpp_conectado:
                res_w = enviar_para_grupo_whatsapp(foto_envio_wpp, texto_wpp)
                print(f"👉 RESPOSTA BAILEYS FILA: {res_w}")
                if res_w.get("sucesso") is True:
                    w_st = "Enviado"
                else:
                    w_st = f"Erro ({res_w.get('erro', 'Falha')})"
            
        registrar_log_envio(
            tipo="CUPOM" if e_cupom_puro else "PRODUTO",
            titulo=titulo,
            canal="@Fila_Reserva",
            wpp_status=w_st,
            tg_status="Enviado",
            link=link_usuario
        )
        print(f"📦 [FILA RESERVA] Oferta postada com foto real e texto original: {titulo}")
        
        limpar_arquivos_temporarios([caminho_foto_local, caminho_story])
    except Exception as e:
        print(f"Erro ao disparar item da fila reserva: {e}")

if __name__ == "__main__":
    varrer_canais()
