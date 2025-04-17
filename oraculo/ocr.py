import streamlit as st
import easyocr
from PIL import Image
import numpy as np

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
