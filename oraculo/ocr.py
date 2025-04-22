import streamlit as st
import easyocr
from PIL import Image
import numpy as np
import os
from pdf2image import convert_from_path
import docx

@st.cache_resource(show_spinner="🔍 Iniciando motor de OCR...")
def carregar_ocr():
    return easyocr.Reader(['pt', 'en'], gpu=False)

def extrair_texto_de_imagem(img_pil: Image.Image) -> str:
    try:
        leitor = carregar_ocr()
        img_array = np.array(img_pil)
        resultado = leitor.readtext(img_array, detail=0, paragraph=True)
        texto = "\n".join(resultado).strip()
        return texto if texto else "[imagem sem texto legível]"
    except Exception as e:
        st.error(f"Erro ao processar imagem com OCR: {e}")
        return "[erro ao processar imagem]"

def extrair_texto_de_pdf(caminho: str) -> str:
    try:
        paginas = convert_from_path(caminho, dpi=300)
        texto_total = ""
        for pagina in paginas:
            texto_total += extrair_texto_de_imagem(pagina) + "\n"
        return texto_total.strip() if texto_total.strip() else "[PDF sem texto legível]"
    except Exception as e:
        st.error(f"Erro ao processar PDF: {e}")
        return "[erro ao processar PDF]"

def extrair_texto_de_docx(caminho: str) -> str:
    try:
        doc = docx.Document(caminho)
        texto = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return texto.strip() if texto else "[Word vazio ou sem texto legível]"
    except Exception as e:
        st.error(f"Erro ao processar DOCX: {e}")
        return "[erro ao processar DOCX]"

def extrair_texto_arquivo(caminho: str) -> str:
    caminho = caminho.lower()
    if caminho.endswith(('.png', '.jpg', '.jpeg')):
        try:
            imagem = Image.open(caminho)
            return extrair_texto_de_imagem(imagem)
        except Exception as e:
            st.warning(f"Erro ao abrir imagem {caminho}: {e}")
            return "[erro ao abrir imagem]"
    elif caminho.endswith('.pdf'):
        return extrair_texto_de_pdf(caminho)
    elif caminho.endswith('.docx'):
        return extrair_texto_de_docx(caminho)
    else:
        return "[formato não suportado para OCR]"
