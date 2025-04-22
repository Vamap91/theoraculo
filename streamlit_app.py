"""
ORÁCULO - Análise Inteligente de Documentos do SharePoint
Aplicação principal Streamlit com suporte melhorado para OCR e processamento de PDFs.
"""

import os
import tempfile
import platform
import streamlit as st
import requests
import io
from PIL import Image
import pytesseract
import time
from openai import OpenAI

# Configuração para o Poppler (necessário para PDFs) - SOLUÇÃO DO ERRO
if platform.system() == "Windows":
    # Adiciona alguns caminhos comuns do Poppler ao PATH
    possible_poppler_paths = [
        r"C:\poppler\bin",
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files (x86)\poppler\bin",
        r"C:\Users\Administrator\AppData\Local\Programs\poppler\bin"
    ]
    
    for path in possible_poppler_paths:
        if os.path.exists(path):
            os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
            break

# Tenta importar o módulo pdf2image
try:
    import pdf2image
    pdf_processor = "pdf2image"
except ImportError:
    pdf_processor = None
    st.warning("Módulo pdf2image não está instalado. Tentando alternativa...")

# Se pdf2image falhar, tenta usar PyMuPDF como alternativa
if pdf_processor is None:
    try:
        import fitz  # PyMuPDF
        pdf_processor = "pymupdf"
    except ImportError:
        pdf_processor = None
        st.error("Nenhum processador de PDF disponível. Instale pdf2image ou pymupdf.")

# Importa os módulos do projeto Oráculo
from oraculo.auth import get_graph_token
from oraculo.scraper import listar_bibliotecas, listar_todos_os_arquivos, baixar_arquivos
from oraculo.ocr import extrair_texto_de_imagem

# Configuração da página Streamlit
st.set_page_config(
    page_title="Oráculo - SharePoint com IA", 
    page_icon="🔮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
SITE_ID = "carglassbr.sharepoint.com,7d0ecc3f-b6c8-411d-8ae4-6d5679a38ca8,e53fc2d9-95b5-4675-813d-769b7a737286"
DATA_DIR = "data"

# Verifica e cria o diretório para armazenar os arquivos, se não existir
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Título e descrição
st.title("🔮 Oráculo - Análise Inteligente de Documentos do SharePoint")
st.markdown("""
Este sistema acessa bibliotecas do SharePoint, extrai texto de documentos visuais e 
permite consultas em linguagem natural usando IA.
""")

# Configuração do OCR e caminhos
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Configuração do OCR
    st.subheader("Configuração do OCR")
    ocr_language = st.selectbox(
        "Idioma principal para OCR:",
        options=["por", "por+eng", "eng"],
        index=1,
        help="Selecione o idioma principal dos documentos"
    )
    
    # Configuração do modelo de IA
    st.subheader("Configuração da IA")
    ai_model = st.selectbox(
        "Modelo OpenAI:",
        options=["gpt-3.5-turbo", "gpt-4"],
        index=0
    )
    
    st.divider()
    
    # Verifica o status do Poppler
    st.subheader("Status do Sistema")
    
    if pdf_processor == "pdf2image":
        try:
            # Verifica se o Poppler está configurado corretamente
            pdf2image.pdfinfo_from_bytes(b"%PDF-1.0\n1 0 obj<</Pages 2 0 R>>/endobj/trailer<</Root 1 0 R>>")
            st.success("✅ Poppler está instalado e configurado corretamente.")
        except Exception as e:
            st.error(f"⚠️ Poppler não está configurado corretamente: {str(e)}")
            st.info("Consulte as instruções para instalar o Poppler.")
    elif pdf_processor == "pymupdf":
        st.success("✅ PyMuPDF está sendo usado para processamento de PDFs.")
    else:
        st.error("❌ Nenhum processador de PDF disponível.")
    
    # Informações do projeto
    st.markdown("### 📋 Sobre o Projeto")
    st.markdown("""
    **Oráculo** é uma ferramenta que:
    - Conecta ao SharePoint via Microsoft Graph API
    - Baixa documentos visuais (imagens e PDFs)
    - Extrai texto via OCR
    - Responde perguntas usando IA
    """)

def extrair_texto_de_pdf_com_pdf2image(pdf_data_or_path):
    """Extrai texto de um PDF usando pdf2image e OCR"""
    try:
        # Se for um caminho para arquivo
        if isinstance(pdf_data_or_path, str):
            if not os.path.exists(pdf_data_or_path):
                return ""
            with open(pdf_data_or_path, 'rb') as f:
                pdf_data = f.read()
        # Se for conteúdo binário
        elif isinstance(pdf_data_or_path, bytes):
            pdf_data = pdf_data_or_path
        else:
            return ""
        
        # Cria um arquivo temporário para o PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_data)
            temp_pdf_path = temp_pdf.name
        
        try:
            # Converte PDF para imagens
            imagens = pdf2image.convert_from_path(temp_pdf_path, dpi=300)
        except Exception as e:
            os.unlink(temp_pdf_path)
            st.error(f"Erro ao converter PDF para imagens: {str(e)}")
            if "Unable to get page count" in str(e):
                st.info("Este erro indica um problema com o Poppler. Veja as instruções na documentação.")
            return f"[erro ao processar PDF: {str(e)}]"
        
        # Remove o arquivo temporário
        os.unlink(temp_pdf_path)
        
        # Extrai texto de cada página
        textos = []
        for i, img in enumerate(imagens):
            texto_pagina = extrair_texto_de_imagem(img, idioma=ocr_language)
            if texto_pagina and texto_pagina != "[imagem sem texto legível]":
                textos.append(f"--- Página {i+1} ---\n{texto_pagina}")
        
        # Combina o texto de todas as páginas
        return "\n\n".join(textos) if textos else "[PDF sem texto legível]"
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return f"[erro ao processar PDF: {str(e)}]"

def extrair_texto_de_pdf_com_pymupdf(pdf_data_or_path):
    """Extrai texto de um PDF usando PyMuPDF (alternativa ao Poppler)"""
    try:
        import fitz  # PyMuPDF
        
        # Se for um caminho para arquivo
        if isinstance(pdf_data_or_path, str):
            if not os.path.exists(pdf_data_or_path):
                return ""
            doc = fitz.open(pdf_data_or_path)
        # Se for conteúdo binário
        elif isinstance(pdf_data_or_path, bytes):
            doc = fitz.open(stream=pdf_data_or_path, filetype="pdf")
        else:
            return ""
        
        # Extrai texto de cada página
        textos = []
        for i in range(len(doc)):
            page = doc[i]
            
            # Tenta extrair texto diretamente
            texto = page.get_text()
            
            # Se a página tiver texto
            if texto.strip():
                textos.append(f"--- Página {i+1} ---\n{texto}")
            else:
                # Se não houver texto, extrai como imagem e aplica OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                
                # Converte para PIL Image
                img_data = pix
