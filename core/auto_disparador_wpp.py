"""
Disparador Automático da Fila do WhatsApp
- Abre o WhatsApp Web com sessão persistente (sessao_whatsapp/)
- Se não estiver logado, aguarda a leitura do QR Code na tela
- Localiza o grupo configurado
- Para cada item na fila:
    1. Envia foto + legenda formatada
    2. Remove o item enviado da fila (ofertas_prontas.json)
    3. Aguarda entre 180 e 300 segundos (3 a 5 minutos) com contagem regressiva
    4. Repete até esvaziar a fila
"""

import os
import sys
import json
import time
import random
from playwright.sync_api import sync_playwright

PASTA_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAMINHO_CONFIG = os.path.join(PASTA_BASE, "config", "configuracoes.json")
CAMINHO_FILA = os.path.join(PASTA_BASE, "fila", "ofertas_prontas.json")
PASTA_SESSAO = os.path.join(PASTA_BASE, "sessao_whatsapp")

if PASTA_BASE not in sys.path:
    sys.path.insert(0, PASTA_BASE)
PASTA_CORE = os.path.join(PASTA_BASE, "core")
if PASTA_CORE not in sys.path:
    sys.path.insert(0, PASTA_CORE)

try:
    from core.formatador_mensagem import formatar_mensagem_whatsapp
except ImportError:
    from formatador_mensagem import formatar_mensagem_whatsapp


def carregar_config():
    if os.path.exists(CAMINHO_CONFIG):
        with open(CAMINHO_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"nome_grupo_whatsapp": "Achadinhos & Ofertas", "adicionar_tag_anuncio": True}

def carregar_fila():
    if os.path.exists(CAMINHO_FILA):
        try:
            with open(CAMINHO_FILA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def salvar_fila(fila):
    with open(CAMINHO_FILA, "w", encoding="utf-8") as f:
        json.dump(fila, f, indent=2, ensure_ascii=False)

def aguardar_com_contagem(segundos: int):
    """Exibe contagem regressiva no terminal."""
    for restante in range(segundos, 0, -1):
        minutos = restante // 60
        segs = restante % 60
        print(f"\r⏳ Próximo envio em: {minutos:02d}:{segs:02d}...", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 45 + "\r", end="", flush=True)

def iniciar_disparador():
    cfg = carregar_config()
    nome_grupo = cfg.get("nome_grupo_whatsapp", "Achadinhos & Ofertas")
    incluir_anuncio = cfg.get("adicionar_tag_anuncio", True)

    fila = carregar_fila()
    if not fila:
        print("⚠️ A fila de ofertas está vazia no momento (fila/ofertas_prontas.json).")
        print("Adicione produtos pelo bot ou painel para disparar.")
        return

    print("=" * 60)
    print(f"🚀 INICIANDO DISPARADOR AUTOMÁTICO DO WHATSAPP")
    print(f"📌 Grupo Alvo: '{nome_grupo}'")
    print(f"📦 Total de ofertas na fila: {len(fila)}")
    print(f"⏱️ Intervalo entre envios: 3 a 5 minutos (aleatório)")
    print("=" * 60)

    os.makedirs(PASTA_SESSAO, exist_ok=True)

    with sync_playwright() as p:
        print("\n🌐 Abrindo navegador do WhatsApp...")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=PASTA_SESSAO,
            headless=False,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")

        # 1. Checa autenticação
        print("🔍 Verificando conexão do WhatsApp...")
        logado = False
        for _ in range(60): # Aguarda até 2 minutos para carregar ou escanear QR Code
            try:
                # Seletor da barra de busca de conversas
                if page.locator('div[contenteditable="true"][data-tab="3"]').is_visible():
                    logado = True
                    break
                # Se houver canvas do QR code visível
                if page.locator('canvas[aria-label*="Scan me"], canvas').is_visible():
                    print("\r📲 Por favor, ESCANEIE O QR CODE na tela com o seu WhatsApp!", end="", flush=True)
            except Exception:
                pass
            time.sleep(2)

        if not logado:
            print("\n❌ Tempo limite esgotado para login. Fechando...")
            browser.close()
            return

        print("\n✅ WhatsApp Conectado com Sucesso!")
        time.sleep(3)

        # 2. Localiza o grupo
        print(f"🔎 Pesquisando grupo '{nome_grupo}'...")
        try:
            campo_busca = page.locator('div[contenteditable="true"][data-tab="3"]').first
            campo_busca.click()
            time.sleep(1)
            campo_busca.fill(nome_grupo)
            time.sleep(2)

            # Clica no grupo
            item_grupo = page.locator(f'span[title="{nome_grupo}"]').first
            item_grupo.wait_for(timeout=15000)
            item_grupo.click()
            print(f"✅ Conversa do grupo '{nome_grupo}' aberta!")
            time.sleep(2)
        except Exception as e:
            print(f"\n❌ Não foi possível encontrar o grupo '{nome_grupo}'.")
            print("Verifique se o nome está idêntico no WhatsApp e em config/configuracoes.json.")
            browser.close()
            return

        # 3. Loop de envio da fila
        indice_envio = 1
        while True:
            fila = carregar_fila()
            if not fila:
                print("\n🎉 Todas as ofertas da fila foram enviadas com sucesso!")
                break

            oferta = fila[0]
            titulo = oferta.get("titulo", "Produto em Oferta")
            preco = oferta.get("preco", "0,00")
            condicao = oferta.get("condicao", "Sem Juros")
            link = oferta.get("link_afiliado", "")
            foto = oferta.get("caminho_imagem") or oferta.get("caminho_story", "")

            print(f"\n📤 [{indice_envio}] Enviando: {titulo[:45]}... (R$ {preco})")

            # Formata o texto idêntico ao modelo de alta conversão
            msg = formatar_mensagem_whatsapp(
                titulo=titulo,
                preco=preco,
                link_afiliado=link,
                condicao=condicao,
                incluir_anuncio=incluir_anuncio
            )

            # Envia foto com legenda
            if not os.path.exists(foto):
                print(f"⚠️ Imagem não encontrada: {foto}. Pulando...")
                fila.pop(0)
                salvar_fila(fila)
                continue

            foto_abs = os.path.abspath(foto)
            sucesso_envio = False

            try:
                # Anexa arquivo
                # Tenta input oculto de imagem
                file_input = page.locator('input[type="file"][accept*="image"]').first
                if not file_input.count():
                    btn_clip = page.locator('button[title="Anexar"], div[title="Anexar"], span[data-icon="plus"]').first
                    btn_clip.click()
                    time.sleep(1)
                    file_input = page.locator('input[type="file"]').first

                file_input.set_input_files(foto_abs)
                time.sleep(3)

                # Caixa de legenda no preview
                caixa_legenda = page.locator('div[contenteditable="true"][data-tab="10"], div[aria-placeholder*="legenda"], div[aria-label*="legenda"]').first
                caixa_legenda.wait_for(timeout=10000)
                caixa_legenda.click()

                # Digita linha por linha com Shift+Enter
                linhas = msg.split("\n")
                for i, l in enumerate(linhas):
                    if l:
                        caixa_legenda.type(l, delay=15)
                    if i < len(linhas) - 1:
                        page.keyboard.press("Shift+Enter")

                time.sleep(1)

                # Clica em enviar
                btn_send = page.locator('span[data-icon="send"], span[data-icon="send-light"]').first
                if btn_send.count():
                    btn_send.click()
                else:
                    page.keyboard.press("Enter")

                time.sleep(4)
                sucesso_envio = True
                print("   ✅ Mensagem e foto entregues no grupo!")

            except Exception as e:
                print(f"   ❌ Falha ao enviar oferta: {e}")

            if sucesso_envio:
                # Remove da fila e salva imediatamente
                fila.pop(0)
                salvar_fila(fila)
                print(f"   🗑️ Oferta removida da fila. Restam {len(fila)} oferta(s).")
                indice_envio += 1

            # Se ainda houver itens, aguarda 3 a 5 minutos (180 a 300 segundos)
            if len(fila) > 0:
                pausa = random.randint(180, 300)
                print(f"   💤 Pausa inteligente de {pausa // 60} min e {pausa % 60} s para segurança...")
                aguardar_com_contagem(pausa)

        print("\n🏁 Finalizado! O navegador permanecerá aberto por 10 segundos antes de fechar.")
        time.sleep(10)
        browser.close()

if __name__ == "__main__":
    iniciar_disparador()
