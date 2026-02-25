import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import os
import webbrowser
import re
import dotenv # <<< Importação carregamento do .env

# Importa as funções dos outros módulos
from database import carregar_dados, ler_cabecalhos
from imagem import mostrar_imagem, atualizar_imagem
from pdf_generator import gerar_pdf

# Carrega varíaveis de ambiente vindas do arquivo .env (se existir)
dotenv.load_dotenv()


class App:
    """
    Aplicação para consulta de preços de produtos com interface gráfica.
    Permite carregar planilhas, filtrar produtos, visualizar imagens e gerar PDFs.
    """
    
    # Constantes da aplicação
    COL_DESCRICAO = 'Descrição'
    COL_PRECO = 'Preço'
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 600
    
    def __init__(self, root):
        """
        Inicializa a aplicação.
        
        Args:
            root: Janela principal do Tkinter
        """
        # Credenciais de API - USAR VARIÁVEIS DE AMBIENTE (.env)
        self.API_KEY = os.getenv('GOOGLE_API_KEY', '')
        self.CX = os.getenv('GOOGLE_CX', '')
        
        # Aviso se as credenciais não estiverem configuradas
        if not self.API_KEY or not self.CX:
            print("AVISO: Credenciais do Google não configuradas no arquivo .env!")
            print("Configure as variáveis de ambiente:")
            print("  - GOOGLE_API_KEY")
            print("  - GOOGLE_CX")
        
        self.root = root
        self.root.title("Consulta de Preços")
        self.root.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)

        # Cache de imagens
        self.cache_imagens = {}
        self.cache_miniaturas = {}

        # --- Variáveis de Dados e Estado ---
        self.df = pd.DataFrame() 
        self.caminho_arquivo = tk.StringVar()
        
        # Variáveis para os nomes das colunas (serão usadas pelos Comboboxes)
        self.nome_coluna_descricao = tk.StringVar(value="") 
        self.nome_coluna_preco = tk.StringVar(value="")
        self.colunas_disponiveis = []
        
        # Dicionário para armazenar o preço numérico real dos itens selecionados
        # Estrutura: {iid: {'preco': float, 'descricao': str, 'preco_formatado': str}}
        self.itens_selecionados_dados = {} 
        
        # --- Configuração de Estilos e Tema ---
        self.style = ttk.Style()
        self.style.theme_use('clam') 
        
        # Estilo para Botões
        self.style.configure('TButton', font=('Arial', 10), padding=6, 
                           relief='flat', background='#dddddd')
        self.style.map('TButton', background=[('active', '#cccccc')])
        
        # Estilo para Treeview (Tabela)
        self.style.configure('Treeview.Heading', font=('Arial', 10, 'bold'), 
                           background='#0078d7', foreground='white')
        self.style.configure('Treeview', font=('Arial', 10), rowheight=25)
        self.style.map('Treeview', background=[('selected', '#0078d7')], 
                      foreground=[('selected', 'white')])

        # Componentes que precisam ser referenciados
        self.combo_descricao = None
        self.combo_preco = None
        self.btn_carregar_dados = None
        self.entry_filtro = None
        self.tree_principal = None
        self.tree_selecionados = None
        self.label_imagem = None
        self.frame_miniaturas = None
        self.label_total_valor = None
        
        # Construir interface
        self.criar_interface()
    
    # ---------------- Funções de Carregamento ---------------- #
    
    def buscar_arquivo(self):
        """
        Abre a caixa de diálogo para buscar o arquivo Excel/CSV.
        Armazena o caminho e inicia a análise das colunas.
        """
        caminho = filedialog.askopenfilename(
            title="Selecione a Planilha de Preços",
            filetypes=(
                ("Arquivos Excel", "*.xlsx *.xls"),
                ("Arquivos CSV", "*.csv"),
                ("Todos os Arquivos", "*.*")
            )
        )
        if caminho:
            self.caminho_arquivo.set(caminho)
            self.analisar_e_popular_colunas()

    def analisar_e_popular_colunas(self):
        """
        Lê o cabeçalho do arquivo selecionado e popula os Comboboxes 
        com as colunas encontradas.
        """
        caminho = self.caminho_arquivo.get()
        if not caminho:
            return

        try:
            # Mostra cursor de espera
            self.root.config(cursor="watch")
            self.root.update()
            
            # Tenta ler os cabeçalhos
            self.colunas_disponiveis = ler_cabecalhos(caminho)
            
            if not self.colunas_disponiveis:
                messagebox.showwarning(
                    "Aviso", 
                    "Nenhuma coluna encontrada.\nArquivo pode estar vazio ou corrompido."
                )
                self.btn_carregar_dados.config(state=tk.DISABLED)
                return

            # Popula os Comboboxes
            self.combo_descricao['values'] = self.colunas_disponiveis
            self.combo_preco['values'] = self.colunas_disponiveis
            
            # Tenta pré-selecionar 'Descrição' e 'Preço' (case-insensitive)
            desc_match = next(
                (col for col in self.colunas_disponiveis if col.lower() == 'descrição'), 
                None
            )
            preco_match = next(
                (col for col in self.colunas_disponiveis if col.lower() == 'preço'), 
                None
            )

            # Define os valores padrão
            self.nome_coluna_descricao.set(
                desc_match if desc_match else self.colunas_disponiveis[0]
            )
            self.nome_coluna_preco.set(
                preco_match if preco_match else self.colunas_disponiveis[0]
            )
            
            # Habilita o botão de carregar dados
            self.btn_carregar_dados.config(state=tk.NORMAL)

        except FileNotFoundError:
            messagebox.showerror("Erro", "Arquivo não encontrado.")
            self._resetar_comboboxes()
        except PermissionError:
            messagebox.showerror("Erro", "Sem permissão para ler o arquivo.")
            self._resetar_comboboxes()
        except Exception as e:
            messagebox.showerror(
                "Erro de Análise", 
                f"Não foi possível ler o cabeçalho da planilha:\n{str(e)}"
            )
            self._resetar_comboboxes()
        finally:
            # Restaura cursor normal
            self.root.config(cursor="")

    def _resetar_comboboxes(self):
        """Helper para resetar os comboboxes em caso de erro."""
        self.colunas_disponiveis = []
        if self.combo_descricao:
            self.combo_descricao['values'] = []
            self.combo_preco['values'] = []
        if self.btn_carregar_dados:
            self.btn_carregar_dados.config(state=tk.DISABLED)
        self.nome_coluna_descricao.set("")
        self.nome_coluna_preco.set("")

    def carregar_planilha(self):
        """
        Carrega o DataFrame usando o caminho e nomes de colunas selecionados.
        Atualiza a tabela principal com os dados carregados.
        """
        caminho = self.caminho_arquivo.get()
        descricao_col = self.nome_coluna_descricao.get().strip()
        preco_col = self.nome_coluna_preco.get().strip()
        
        if not caminho or not descricao_col or not preco_col:
            messagebox.showwarning(
                "Aviso", 
                "Selecione o arquivo e as colunas de Descrição e Preço."
            )
            return

        try:
            # Mostra cursor de espera
            self.root.config(cursor="watch")
            self.root.update()
            
            # Chama a função do database.py com o caminho e os nomes das colunas
            self.df = carregar_dados(caminho, descricao_col, preco_col)
            
            messagebox.showinfo(
                "Sucesso", 
                f"Planilha carregada com sucesso!\nTotal de {len(self.df)} linhas."
            )
            
            # Limpa dados anteriores e exibe os novos dados
            self.itens_selecionados_dados.clear()
            for item in self.tree_selecionados.get_children():
                self.tree_selecionados.delete(item)
            self.calcular_total()
            
            self.limpar_filtro()
            self.atualizar_tabela()

        except FileNotFoundError:
            messagebox.showerror("Erro", "Arquivo não encontrado.")
            self.df = pd.DataFrame()
        except PermissionError:
            messagebox.showerror("Erro", "Sem permissão para ler o arquivo.")
            self.df = pd.DataFrame()
        except Exception as e:
            messagebox.showerror(
                "Erro de Carregamento", 
                f"Não foi possível carregar a planilha:\n{str(e)}"
            )
            self.df = pd.DataFrame()
        finally:
            # Restaura cursor normal
            self.root.config(cursor="")

    # ---------------- Funções principais ---------------- #
    
    def atualizar_tabela(self, *_):
        """
        Atualiza a tabela principal com os dados do DataFrame.
        Aplica o filtro de busca se houver texto no campo de filtro.
        """
        # Proteção: Se o DataFrame estiver vazio, limpa o grid e sai
        if self.df.empty:
            for item in self.tree_principal.get_children():
                self.tree_principal.delete(item)
            return

        # Limpa a tabela
        for item in self.tree_principal.get_children():
            self.tree_principal.delete(item)

        # Aplica o filtro
        filtro = self.entry_filtro.get().lower().strip()
        df_filtrado = self.df

        if filtro:
            # Filtro fuzzy (busca por palavras soltas na ordem)
            pattern = '.*'.join(map(re.escape, filtro.split()))
            df_filtrado = self.df[
                self.df[self.COL_DESCRICAO].str.contains(pattern, case=False, na=False)
            ]

        # Popula a tabela com os dados filtrados
        for index, row in df_filtrado.iterrows():
            # Obtém o preço numérico
            preco_num = row[self.COL_PRECO]
            
            # Formatação segura do preço para exibição
            preco_formatado = self._formatar_preco(preco_num)
            
            # Verifica se o item já foi selecionado (não adiciona novamente)
            if str(index) not in self.itens_selecionados_dados:
                self.tree_principal.insert(
                    '', 'end', 
                    iid=str(index),
                    values=(row[self.COL_DESCRICAO], preco_formatado)
                )

        # Ajuste de largura da coluna de descrição
        if not df_filtrado.empty:
            max_len = max(
                (len(str(r[self.COL_DESCRICAO])) for _, r in df_filtrado.iterrows()), 
                default=10
            )
            largura = min(500, max(200, max_len * 10))
            self.tree_principal.column("Descrição", anchor='w', width=largura)

    def _formatar_preco(self, preco_num):
        """
        Formata o preço para o padrão brasileiro (R$ X.XXX,XX).
        
        Args:
            preco_num: Valor numérico do preço
            
        Returns:
            String com o preço formatado ou mensagem de erro
        """
        try:
            if pd.isna(preco_num):
                return "Preço não disponível"
            
            preco_float = float(preco_num)
            
            # Formata com separador de milhar e 2 casas decimais
            # Python usa formato americano: 1,000.00
            preco_formatado = f"{preco_float:,.2f}"
            
            # Converte para formato brasileiro: 1.000,00
            # 1. Troca vírgula (milhar americano) por um placeholder
            # 2. Troca ponto (decimal americano) por vírgula (decimal brasileiro)
            # 3. Troca placeholder por ponto (milhar brasileiro)
            preco_formatado = preco_formatado.replace(",", "TEMP")
            preco_formatado = preco_formatado.replace(".", ",")
            preco_formatado = preco_formatado.replace("TEMP", ".")
            
            return f"R$ {preco_formatado}"
            
        except (ValueError, TypeError):
            return "Preço não disponível"

    def adicionar_selecionados(self):
        """
        Adiciona os itens selecionados da tabela principal para a tabela de selecionados.
        Remove da tabela principal para evitar duplicação e atualiza o total.
        """
        selecionados = self.tree_principal.selection()
        
        if not selecionados:
            return
        
        for item_id in selecionados:
            valores = self.tree_principal.item(item_id, 'values')
            
            if not valores or len(valores) < 2:
                continue
            
            # Pega o preço numérico do DataFrame original
            try:
                index_df = int(item_id)
                if index_df not in self.df.index:
                    continue
                    
                preco_num = self.df.loc[index_df, self.COL_PRECO]
                
                # Converte para float de forma segura
                try:
                    preco_float = float(preco_num) if pd.notna(preco_num) else 0.0
                except (ValueError, TypeError):
                    preco_float = 0.0
                
                # Insere na tabela de selecionados
                self.tree_selecionados.insert('', 'end', iid=item_id, values=valores)
                
                # Salva os dados completos do item
                self.itens_selecionados_dados[item_id] = {
                    'preco': preco_float,
                    'descricao': valores[0],
                    'preco_formatado': valores[1]
                }
                
                # Remove da tabela principal
                self.tree_principal.delete(item_id)
                
            except (ValueError, KeyError, IndexError) as e:
                print(f"Erro ao adicionar item {item_id}: {e}")
                continue
        
        self.calcular_total()

    def remover_selecionado(self, *_):
        """
        Remove os itens selecionados da tabela de selecionados.
        Reinsere os itens na tabela principal se ainda existirem no DataFrame.
        """
        selecionados = self.tree_selecionados.selection()
        
        if not selecionados:
            return
        
        for item_id in selecionados:
            valores = self.tree_selecionados.item(item_id, 'values')
            
            # Remove do dicionário de dados
            if item_id in self.itens_selecionados_dados:
                del self.itens_selecionados_dados[item_id]

            # Reinsere na tabela principal se o item existir no DF
            try:
                original_index = int(item_id)
                if original_index in self.df.index:
                    # Verifica se passa pelo filtro atual
                    filtro = self.entry_filtro.get().lower().strip()
                    descricao = self.df.loc[original_index, self.COL_DESCRICAO]
                    
                    if not filtro or filtro.lower() in str(descricao).lower():
                        self.tree_principal.insert('', 'end', iid=item_id, values=valores)
                        
            except (ValueError, KeyError):
                pass
            
            # Remove da tabela de selecionados
            self.tree_selecionados.delete(item_id)
        
        self.calcular_total()

    def limpar_filtro(self):
        """Limpa o campo de filtro e atualiza a tabela."""
        self.entry_filtro.delete(0, tk.END)
        self.atualizar_tabela()

    def calcular_total(self):
        """Calcula e exibe o total dos itens selecionados."""
        total = sum(
            item['preco'] 
            for item in self.itens_selecionados_dados.values()
        )
        
        # Formatação do total
        total_formatado = self._formatar_preco(total)
        self.label_total_valor.config(text=total_formatado)

    # ---------------- Função Google ---------------- #
    
    def abrir_google_imagens(self, event):
        """
        Abre o navegador e faz uma pesquisa no Google Imagens usando 
        a descrição do item selecionado.
        
        Args:
            event: Evento do clique duplo
        """
        item = self.tree_principal.identify_row(event.y)
        if not item:
            return
        
        valores = self.tree_principal.item(item, 'values')
        if not valores:
            return
        
        descricao = valores[0]
        
        # Limpa a descrição removendo caracteres especiais
        descricao_limpa = descricao.replace(" - ", " ").replace("-", " ").strip()
        query = descricao_limpa.replace(" ", "+")
        
        # URL do Google Imagens
        url = f"https://www.google.com/search?tbm=isch&q={query}"
        
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror(
                "Erro", 
                f"Não foi possível abrir o navegador:\n{str(e)}"
            )

    # ---------------- Interface ---------------- #
    
    def criar_interface(self):
        """Cria todos os componentes da interface gráfica."""
        # Configura a expansão do container principal
        self.root.grid_rowconfigure(0, weight=1) 
        self.root.grid_columnconfigure(0, weight=1)

        # --- FRAME PRINCIPAL ---
        self.main_container = tk.Frame(self.root, padx=15, pady=15)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        
        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # --- FRAME DE CONTEÚDO ---
        content_frame = tk.Frame(self.main_container)
        content_frame.grid(row=0, column=0, rowspan=6, sticky="nsew", padx=(0, 15))
        
        content_frame.grid_rowconfigure(3, weight=1)
        content_frame.grid_rowconfigure(5, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # --- FRAME DE CARREGAMENTO ---
        frame_carregamento = tk.Frame(content_frame)
        frame_carregamento.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        frame_carregamento.columnconfigure(0, weight=1)

        # Seleção de Arquivo
        tk.Entry(
            frame_carregamento, 
            textvariable=self.caminho_arquivo, 
            width=60, 
            state='readonly', 
            justify='left', 
            bd=2, 
            relief='sunken'
        ).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        ttk.Button(
            frame_carregamento, 
            text="Buscar Planilha", 
            command=self.buscar_arquivo
        ).grid(row=0, column=1, padx=5)
        
        # Botão Carregar Dados
        self.btn_carregar_dados = tk.Button(
            frame_carregamento, 
            text="Carregar Dados", 
            command=self.carregar_planilha, 
            state=tk.DISABLED
        )
        self.btn_carregar_dados.grid(row=0, column=2, padx=(5, 0))

        # --- FRAME SELEÇÃO DAS COLUNAS ---
        frame_colunas = tk.Frame(content_frame)
        frame_colunas.grid(row=1, column=0, pady=(5, 10), sticky="ew")
        frame_colunas.columnconfigure(1, weight=1)
        frame_colunas.columnconfigure(3, weight=1)
        
        tk.Label(frame_colunas, text="Coluna Descrição:").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.combo_descricao = ttk.Combobox(
            frame_colunas, 
            textvariable=self.nome_coluna_descricao, 
            state="readonly"
        )
        self.combo_descricao.grid(row=0, column=1, sticky="ew", padx=5)

        tk.Label(frame_colunas, text="Coluna Preço:").grid(
            row=0, column=2, sticky="w", padx=(15, 5)
        )
        self.combo_preco = ttk.Combobox(
            frame_colunas, 
            textvariable=self.nome_coluna_preco, 
            state="readonly"
        )
        self.combo_preco.grid(row=0, column=3, sticky="ew", padx=(5, 0))

        # --- FRAME FILTRO ---
        frame_filtro = tk.Frame(content_frame)
        frame_filtro.grid(row=2, column=0, pady=(5, 10), sticky="ew")
        frame_filtro.columnconfigure(1, weight=1)

        tk.Label(frame_filtro, text="Digite o nome do produto:").grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.entry_filtro = tk.Entry(frame_filtro)
        self.entry_filtro.grid(row=0, column=1, sticky="ew", padx=5)
        self.entry_filtro.bind("<KeyRelease>", self.atualizar_tabela)

        ttk.Button(
            frame_filtro, 
            text="Limpar Filtro", 
            command=self.limpar_filtro
        ).grid(row=0, column=2, padx=10)

        # --- TREEVIEW PRINCIPAL ---
        self.tree_principal = ttk.Treeview(
            content_frame, 
            columns=("Descrição", "Preço"), 
            style='Treeview', 
            show="headings", 
            selectmode="extended"
        )
        self.tree_principal.heading("Descrição", text="Descrição")
        self.tree_principal.heading("Preço", text="Preço")
        self.tree_principal.grid(row=3, column=0, sticky="nsew")

        scroll_principal = ttk.Scrollbar(
            content_frame, 
            orient="vertical", 
            command=self.tree_principal.yview
        )
        self.tree_principal.configure(yscroll=scroll_principal.set)
        scroll_principal.grid(row=3, column=0, sticky='nse')

        # Configuração das colunas - Ambas ajustáveis manualmente
        self.tree_principal.column("Descrição", anchor='w', width=400, minwidth=100, stretch=False)
        self.tree_principal.column("Preço", anchor='e', width=120, minwidth=80, stretch=False)

        # Bindings
        self.tree_principal.bind("<ButtonRelease-1>", lambda e: mostrar_imagem(self))
        self.tree_principal.bind("<Double-1>", self.abrir_google_imagens)

        # --- BOTÃO ADICIONAR ---
        ttk.Button(
            content_frame, 
            text="Adicionar Selecionados", 
            command=self.adicionar_selecionados
        ).grid(row=4, column=0, pady=10, padx=10, sticky="n")

        # --- TREEVIEW SELECIONADOS ---
        self.tree_selecionados = ttk.Treeview(
            content_frame, 
            columns=("Descrição", "Preço"), 
            style='Treeview', 
            show="headings", 
            selectmode="browse"
        )
        self.tree_selecionados.heading("Descrição", text="Descrição")
        self.tree_selecionados.heading("Preço", text="Preço")
        self.tree_selecionados.grid(row=5, column=0, sticky="nsew")

        scroll_sel = ttk.Scrollbar(
            content_frame, 
            orient="vertical", 
            command=self.tree_selecionados.yview
        )
        self.tree_selecionados.configure(yscroll=scroll_sel.set)
        scroll_sel.grid(row=5, column=0, sticky='nse')

        # Configuração das colunas - Ambas ajustáveis manualmente
        self.tree_selecionados.column("Descrição", anchor='w', width=400, minwidth=100, stretch=False)
        self.tree_selecionados.column("Preço", anchor='e', width=120, minwidth=80, stretch=False)
        self.tree_selecionados.bind("<Double-1>", self.remover_selecionado)

        # --- BOTÃO GERAR PDF ---
        tk.Button(
            content_frame, 
            text="Gerar PDF", 
            command=lambda: gerar_pdf(self)
        ).grid(row=6, column=0, pady=10, padx=10, sticky="n")

        # --- FRAME TOTAL ---
        frame_total = tk.Frame(content_frame)
        frame_total.grid(row=7, column=0, pady=(5, 0), sticky="w")

        tk.Label(frame_total, text="Total:", font=('Arial', 12, 'bold')).grid(
            row=0, column=0, sticky="w"
        )
        self.label_total_valor = tk.Label(
            frame_total, 
            text="R$ 0,00", 
            font=('Arial', 12, 'bold'), 
            fg="red"
        )
        self.label_total_valor.grid(row=0, column=1, sticky="w", padx=(5, 0))

        # --- FRAME IMAGEM ---
        frame_img = tk.Frame(self.main_container, bd=2, relief="groove")
        frame_img.grid(row=0, column=1, rowspan=8, padx=(15, 0), sticky="nsew")
        
        # Área de exibição da imagem
        self.label_imagem = tk.Label(
            frame_img, 
            text="Imagem do produto", 
            bg="lightgray", 
            width=30, 
            height=15, 
            relief="sunken", 
            anchor="center"
        )
        self.label_imagem.pack(padx=10, pady=10)

        # Frame miniaturas
        self.frame_miniaturas = tk.Frame(frame_img)
        self.frame_miniaturas.pack(pady=5, padx=10)

        # Botão atualizar imagem
        ttk.Button(
            frame_img, 
            text="Atualizar Imagem", 
            command=lambda: atualizar_imagem(self)
        ).pack(pady=5, padx=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()