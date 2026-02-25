import pandas as pd
import warnings 

# Adiciona um filtro para ignorar a UserWarning específica do openpyxl
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl") 

def ler_cabecalhos(caminho_arquivo: str) -> list:
    """
    Lê apenas o cabeçalho do arquivo Excel para retornar os nomes das colunas.
    
    Args:
        caminho_arquivo (str): O caminho completo do arquivo Excel.
        
    Returns:
        list: Uma lista de strings contendo os nomes das colunas.
        
    Raises:
        Exception: Em caso de falha na leitura.
    """
    if not caminho_arquivo:
        return []

    try:
        # Lê apenas a primeira linha (header=0) e usa nrows=0 para ler apenas a estrutura
        df_header = pd.read_excel(caminho_arquivo, header=0, nrows=0)
        # Limpa e retorna os nomes das colunas
        return [col.strip() for col in df_header.columns]
        
    except Exception as e:
        # Relança o erro para ser tratado pela UI
        raise Exception(f"Falha ao ler o cabeçalho da planilha. Verifique o formato do arquivo: {e}")


def carregar_dados(caminho_arquivo: str, nome_col_descricao: str, nome_col_preco: str) -> pd.DataFrame:
    """
    Carrega, formata e valida os dados de Descrição e Preço de um arquivo Excel,
    usando nomes de colunas fornecidos pelo usuário.
    
    A função lê APENAS as colunas especificadas e as renomeia internamente para
    'Descrição' e 'Preço', garantindo que o resto do código (UI, PDF) funcione.
    
    Args:
        caminho_arquivo (str): O caminho completo do arquivo Excel.
        nome_col_descricao (str): O nome da coluna no arquivo que contém a descrição.
        nome_col_preco (str): O nome da coluna no arquivo que contém o preço.
        
    Returns:
        pd.DataFrame: O DataFrame carregado com as colunas padronizadas 'Descrição' e 'Preço'.
        
    Raises:
        Exception: Em caso de falha na leitura, formatação ou falta das colunas essenciais.
    """
    
    if not caminho_arquivo:
        raise ValueError("O caminho do arquivo não pode ser vazio.")
        
    colunas_necessarias = [nome_col_descricao, nome_col_preco]

    try:
        # 1. Leitura da Planilha: Lê SOMENTE as colunas especificadas pelo usuário.
        df = pd.read_excel(caminho_arquivo, usecols=colunas_necessarias, header=0)
        
        # 2. Limpeza de Cabeçalhos e Mapeamento
        df.columns = df.columns.str.strip()
        
        # 3. Validação das Colunas Essenciais (Verifica se as colunas lidas correspondem ao esperado)
        # Verifica se os nomes lidos (após strip) estão no DataFrame
        descricao_col_strip = nome_col_descricao.strip()
        preco_col_strip = nome_col_preco.strip()
        
        if descricao_col_strip not in df.columns or preco_col_strip not in df.columns:
             # Isso deve ser raro se o usecols funcionou, mas é um bom backup.
             raise KeyError(f"Uma ou ambas as colunas especificadas ('{nome_col_descricao}' e '{nome_col_preco}') não foram encontradas na planilha.")
        
        # 4. Renomear Colunas para Padrão Interno ('Descrição' e 'Preço')
        # Isso garante que a UI e o PDF usem sempre os mesmos nomes, independentemente do nome original.
        df = df.rename(columns={
            descricao_col_strip: 'Descrição',
            preco_col_strip: 'Preço'
        })
            
        # 5. Formatação da Coluna de Preço
        # Converte a coluna 'Preço' para numérica (valores inválidos viram NaN).
        df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce')
        
        # 6. Filtra linhas sem descrição ou preço válido
        df = df.dropna(subset=['Descrição', 'Preço'])
        
        return df

    except Exception as e:
        # Captura e relança o erro com uma mensagem amigável
        raise Exception(f"Falha ao processar a planilha. Verifique se as colunas '{nome_col_descricao}' e '{nome_col_preco}' existem e se o arquivo está no formato correto (Excel/CSV): {e}")