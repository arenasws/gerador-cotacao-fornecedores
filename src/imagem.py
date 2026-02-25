import threading
import requests
from io import BytesIO
from PIL import Image, ImageTk
import re
import tkinter as tk

def formatar_descricao(descricao):
    """
    Limpa e formata a descrição do produto para uso como query de pesquisa na API do Google.
    Substitui caracteres especiais por espaço e depois espaços por '+'.
    """
    # Limita o tamanho para otimizar a pesquisa
    descricao = descricao[:60]
    # 1. Substitui todos os caracteres que não são letras, números ou espaços por um espaço simples
    # Isso transforma hífens, pontuações, etc., em espaços.
    descricao_limpa = re.sub(r'[^a-zA-Z0-9\s]', ' ', descricao)
    # 2. Substitui múltiplos espaços por um único espaço e remove espaços iniciais/finais
    descricao_limpa = re.sub(r'\s+', ' ', descricao_limpa).strip()
    # 3. Substitui os espaços restantes por '+' para codificação da URL (query)
    query = descricao_limpa.replace(" ", "+") 
    return query

def mostrar_imagem(app, force_update=False):
    selected_item = app.tree_principal.selection()
    if not selected_item:
        return

    descricao = app.tree_principal.item(selected_item[0], 'values')[0]
    
    # Atualização de UI no thread principal: Label de carregamento
    app.label_imagem.config(text="Carregando imagem...", image="", compound="center")

    # Verifica cache
    if not force_update and descricao in app.cache_imagens:
        # Atualização de UI no thread principal
        app.label_imagem.config(image=app.cache_imagens[descricao], text="")
        exibir_miniaturas(app, descricao)
        return

    def buscar_imagens():
        miniaturas = []
        try:
            # Garante que a query será limpa e formatada corretamente com '+'
            query = formatar_descricao(descricao) + "+produto+computador+informatica"
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "q": query,
                "cx": app.CX,
                "key": app.API_KEY,
                "searchType": "image",
                "num": 5, # Pega 5 imagens
                "imgType": "photo",
                "imgSize": "medium",
                "safe": "active"
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if "items" not in data:
                # Agenda mensagem de erro na thread principal
                app.root.after(0, lambda: app.label_imagem.config(text="Nenhuma imagem encontrada", image="", compound="center"))
                return

            
            url_primeira_imagem = None
            for item in data["items"]:
                img_url = item["link"]
                if url_primeira_imagem is None:
                    url_primeira_imagem = img_url # Salva a primeira URL para o display principal
                    
                try:
                    # Tenta baixar os dados da imagem (timeout para não travar)
                    img_data = requests.get(img_url, timeout=5).content
                    
                    # Tenta abrir e redimensionar a imagem
                    img = Image.open(BytesIO(img_data))
                    # Ajusta para 100x100 para miniaturas
                    img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                    # PIL.Image precisa ser convertido para PhotoImage do Tkinter
                    img_tk = ImageTk.PhotoImage(img)
                    miniaturas.append((img_tk, img_url))

                except Exception as img_e:
                    # Este bloco captura "cannot identify image file" e outros erros
                    print(f"Erro ao processar imagem de URL {img_url}: {img_e}")
                    continue

            if not miniaturas:
                # Agenda mensagem de erro na thread principal
                app.root.after(0, lambda: app.label_imagem.config(text="Nenhuma imagem encontrada", image="", compound="center"))
                return

            # Processa a primeira imagem para o display principal (tamanho maior)
            img_data_principal = requests.get(url_primeira_imagem, timeout=5).content
            img_principal = Image.open(BytesIO(img_data_principal))
            img_principal.thumbnail((300, 300), Image.Resampling.LANCZOS) 
            img_tk_principal = ImageTk.PhotoImage(img_principal)

            # --- Atualizações de Cache e UI (Agendadas para a thread principal) ---
            app.cache_miniaturas[descricao] = miniaturas
            app.cache_imagens[descricao] = img_tk_principal
            
            # Agendamento das atualizações de UI
            def atualizar_ui_sucesso():
                # Exibe a imagem principal
                app.label_imagem.config(image=app.cache_imagens[descricao], text="")
                # Exibe as miniaturas
                exibir_miniaturas(app, descricao)
            
            app.root.after(0, atualizar_ui_sucesso)


        except Exception as e:
            print(f"Erro ao buscar imagens: {e}")
            # CORREÇÃO: Captura a variável de exceção 'e' no lambda usando default argument
            app.root.after(0, lambda error_e=e: app.label_imagem.config(text=f"Erro: {error_e}", image="", compound="center"))

    threading.Thread(target=buscar_imagens, daemon=True).start()


def atualizar_imagem(app):
    selected_item = app.tree_principal.selection()
    if not selected_item:
        return
    descricao = app.tree_principal.item(selected_item[0], 'values')[0]
    # Limpa os caches para forçar nova busca
    if descricao in app.cache_imagens:
        del app.cache_imagens[descricao]
    if descricao in app.cache_miniaturas:
        del app.cache_miniaturas[descricao]
        # Limpa o frame de miniaturas (UI update)
        for widget in app.frame_miniaturas.winfo_children():
            widget.destroy()
            
    # Chama a função principal para iniciar a nova busca
    mostrar_imagem(app, force_update=True)


def exibir_miniaturas(app, descricao):
    # Limpa miniaturas antigas
    for widget in app.frame_miniaturas.winfo_children():
        widget.destroy()

    miniaturas = app.cache_miniaturas.get(descricao, [])
    # Garante que as miniaturas são exibidas na thread principal
    for idx, (img_tk, _) in enumerate(miniaturas):
        # É crucial que o botão mantenha uma referência à ImageTk.PhotoImage (por isso o btn.image = img_tk)
        btn = tk.Button(app.frame_miniaturas, image=img_tk,
                        command=lambda i=idx: selecionar_miniatura(app, descricao, i))
        btn.image = img_tk 
        btn.pack(side="left", padx=2)

def selecionar_miniatura(app, descricao, idx):
    miniaturas = app.cache_miniaturas.get(descricao)
    if miniaturas and idx < len(miniaturas):
        img_url = miniaturas[idx][1]
        
        # Redimensionamento e exibição da imagem principal em thread
        def carregar_principal():
            try:
                img_data = requests.get(img_url, timeout=5).content
                img_principal = Image.open(BytesIO(img_data))
                img_principal.thumbnail((300, 300), Image.Resampling.LANCZOS)
                img_tk_principal = ImageTk.PhotoImage(img_principal)
                
                # Atualização de UI na thread principal
                app.root.after(0, lambda: app.label_imagem.config(image=img_tk_principal, text=""))
                # Manter a referência forte
                app.cache_imagens[descricao] = img_tk_principal
                
            except Exception as e:
                print(f"Erro ao selecionar miniatura: {e}")
                # CORREÇÃO: Captura a variável de exceção 'e' no lambda usando default argument
                app.root.after(0, lambda error_e=e: app.label_imagem.config(text=f"Erro ao carregar: {error_e}", image="", compound="center"))
        
        threading.Thread(target=carregar_principal, daemon=True).start()