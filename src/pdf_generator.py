import tkinter as tk
from tkinter import messagebox, filedialog
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
import time
import os
import platform


def abrir_pdf_automaticamente(caminho_arquivo):
    """
    Tenta abrir o arquivo PDF no visualizador padrão do sistema operacional.
    
    Args:
        caminho_arquivo: Caminho completo do arquivo PDF a ser aberto
    """
    try:
        if platform.system() == 'Windows':
            # Comando no Windows
            os.startfile(caminho_arquivo)
        elif platform.system() == 'Darwin':
            # Comando no macOS
            os.system(f'open "{caminho_arquivo}"')
        else:
            # Comando no Linux (usa 'xdg-open' ou 'gnome-open')
            os.system(f'xdg-open "{caminho_arquivo}"')
    except Exception as e:
        # Se falhar, apenas imprime um aviso no console
        print(f"Aviso: Não foi possível abrir o PDF automaticamente. Erro: {e}")


def gerar_pdf(app):
    """
    Gera um relatório PDF com os itens selecionados e o preço total.
    Solicita ao usuário o local para salvar o arquivo e abre-o em seguida.
    
    Args:
        app: Instância da aplicação principal contendo os dados
    """
    
    itens_selecionados = app.tree_selecionados.get_children()
    if not itens_selecionados:
        messagebox.showwarning("Aviso", "A lista de itens selecionados está vazia.")
        return

    # 1. Solicita o local e nome do arquivo ao usuário
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    nome_padrao = f"Lista_de_Precos_{timestamp}.pdf"
    
    nome_arquivo = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        initialfile=nome_padrao,
        title="Salvar Relatório PDF",
        filetypes=[("Arquivos PDF", "*.pdf")]
    )
    
    # Se o usuário cancelar a operação, a função retorna
    if not nome_arquivo:
        return

    try:
        # 2. Configuração do Documento
        doc = SimpleDocTemplate(
            nome_arquivo, 
            pagesize=A4, 
            leftMargin=0.5*inch, 
            rightMargin=0.5*inch,
            topMargin=0.5*inch, 
            bottomMargin=0.5*inch
        )
        
        styles = getSampleStyleSheet()
        flowables = []
        
        # 3. Título do Relatório - CORREÇÃO AQUI
        # Cria um estilo personalizado para título centralizado
        titulo_style = ParagraphStyle(
            'TituloCentralizado',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=16,
            spaceAfter=12
        )
        
        titulo = Paragraph(
            f"Relatório de Cotação - Data: {time.strftime('%d/%m/%Y')}", 
            titulo_style
        )
        flowables.append(titulo)
        flowables.append(Spacer(1, 0.25*inch))
        
        # 4. Preparação dos Dados da Tabela
        tabela_data = [['#', 'Descrição do Produto', 'Preço Unitário']]
        total_geral = 0.0

        # Iterar sobre os itens selecionados
        for i, item_id in enumerate(itens_selecionados):
            valores_tabela = app.tree_selecionados.item(item_id, 'values')
            descricao = valores_tabela[0]
            preco_formatado = valores_tabela[1]
            
            # Pega o preço numérico do dicionário de dados
            preco_num = app.itens_selecionados_dados.get(item_id, {}).get('preco', 0.0)
            total_geral += preco_num

            tabela_data.append([
                str(i + 1), 
                Paragraph(descricao, styles['Normal']),
                preco_formatado
            ])

        # 5. Adiciona a linha de Total
        # Formata o total no padrão brasileiro
        total_formatado = f"{total_geral:,.2f}"
        total_formatado = total_formatado.replace(",", "TEMP")
        total_formatado = total_formatado.replace(".", ",")
        total_formatado = total_formatado.replace("TEMP", ".")
        total_formatado = f"R$ {total_formatado}"
        
        # Linha do Total: merge das duas primeiras colunas
        tabela_data.append([
            '', 
            Paragraph('<b>TOTAL GERAL</b>', styles['Normal']), 
            Paragraph(f'<b>{total_formatado}</b>', styles['Normal'])
        ])
        
        # 6. Cria a Tabela
        tabela = Table(tabela_data, colWidths=[0.5*inch, 4.5*inch, 1.5*inch])
        
        # 7. Estilo da Tabela
        tabela.setStyle(TableStyle([
            # Cabeçalho
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),  # Preços à direita
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # Linhas de dados
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.grey),
            
            # Estilo da linha do Total
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('SPAN', (0, -1), (1, -1)),
            ('ALIGN', (0, -1), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, -1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 4),
        ]))

        flowables.append(tabela)
        
        # 8. Gera o PDF
        doc.build(flowables)
        
        # 9. Feedback e Abertura Automática
        messagebox.showinfo(
            "Sucesso", 
            f"PDF gerado com sucesso!\n\nArquivo salvo em:\n{nome_arquivo}"
        )
        abrir_pdf_automaticamente(nome_arquivo)

    except PermissionError:
        messagebox.showerror(
            "Erro de Permissão", 
            "Não foi possível salvar o arquivo.\n"
            "Verifique se você tem permissão para salvar neste local."
        )
    except Exception as e:
        messagebox.showerror(
            "Erro ao Gerar PDF", 
            f"Ocorreu um erro inesperado ao gerar o PDF:\n{str(e)}"
        )