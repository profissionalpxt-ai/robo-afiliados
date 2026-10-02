"""
Módulo de Automação do WhatsApp Web via Playwright
- Mantém sessão salva permanentemente em 'sessao_whatsapp/' (não pede QR Code toda hora)
- Localiza o grupo pelo nome exato configurado
- Anexa a foto e adiciona o texto formatado como legenda (caption)
- Envia imagem + texto juntos em uma única mensagem elegante
"""

import os
import time
from playwright.sync_api import sync_playwright

PASTA_SESSAO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sessao_whatsapp"))

class WhatsAppBot:
    def __init__(self, pasta_sessao: str = PASTA_SESSAO):
        self.pasta_sessao = pasta_sessao
        os.makedirs(self.pasta_sessao, exist_ok=True)

    def abrir_para_login(self):
        """
        Abre o navegador visível para o usuário escanear o QR Code pela primeira vez.
        A sessão fica salva na pasta 'sessao_whatsapp'.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=self.pasta_sessao,
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://web.whatsapp.com")
            print("Navegador aberto! Escaneie o QR Code caso ainda não esteja conectado.")
            
            # Aguarda carregar a lista de conversas
            try:
                page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=120000)
                print("WhatsApp conectado com sucesso!")
            except Exception:
                print("Tempo limite aguardando conexão.")
            finally:
                browser.close()

    def enviar_oferta(self, nome_grupo: str, caminho_foto: str, texto_legenda: str) -> dict:
        """
        Envia a foto do produto com o texto formatado no grupo do WhatsApp.
        """
        if not os.path.exists(caminho_foto):
            return {"sucesso": False, "erro": f"Arquivo de foto não encontrado: {caminho_foto}"}

        caminho_foto_abs = os.path.abspath(caminho_foto)

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.pasta_sessao,
                    headless=False, # Manter visível para segurança e visualização
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto("https://web.whatsapp.com")

                # 1. Aguarda WhatsApp Web carregar
                print("Aguardando carregamento do WhatsApp Web...")
                page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=60000)
                time.sleep(2)

                # 2. Pesquisa o grupo
                campo_busca = page.locator('div[contenteditable="true"][data-tab="3"]').first
                campo_busca.click()
                campo_busca.fill(nome_grupo)
                time.sleep(2)

                # 3. Clica no grupo encontrado
                item_conversa = page.locator(f'span[title="{nome_grupo}"]').first
                item_conversa.wait_for(timeout=10000)
                item_conversa.click()
                time.sleep(2)

                # 4. Anexa a foto usando o input file oculto do WhatsApp
                file_input = page.locator('input[type="file"][accept*="image"]')
                if not file_input.count():
                    # Clica no botão de '+' ou clip
                    btn_clip = page.locator('button[title="Anexar"], div[title="Anexar"], span[data-icon="plus"]').first
                    btn_clip.click()
                    time.sleep(1)
                    file_input = page.locator('input[type="file"]').first

                file_input.set_input_files(caminho_foto_abs)
                time.sleep(3)

                # 5. Adiciona a legenda no preview da imagem
                # Caixa de texto de legenda do WhatsApp Web
                caixa_legenda = page.locator('div[contenteditable="true"][data-tab="10"], div[aria-placeholder*="legenda"], div[aria-label*="legenda"]').first
                caixa_legenda.wait_for(timeout=10000)
                caixa_legenda.click()
                
                # Preenche linha por linha simulando Shift+Enter para quebras de linha perfeitas
                linhas = texto_legenda.split("\n")
                for i, linha in enumerate(linhas):
                    if linha:
                        caixa_legenda.type(linha, delay=20)
                    if i < len(linhas) - 1:
                        page.keyboard.press("Shift+Enter")
                
                time.sleep(1)

                # 6. Clica no botão de enviar (ícone verde de aviãozinho)
                btn_enviar = page.locator('span[data-icon="send"], span[data-icon="send-light"]').first
                if btn_enviar.count():
                    btn_enviar.click()
                else:
                    page.keyboard.press("Enter")

                # Aguarda confirmação do envio
                time.sleep(5)
                browser.close()
                return {"sucesso": True, "mensagem": "Oferta enviada com sucesso no grupo!"}

            except Exception as e:
                try:
                    browser.close()
                except Exception:
                    pass
                return {"sucesso": False, "erro": str(e)}
