import streamlit as st
import pytesseract
from PIL import Image
import numpy as np

@st.cache_resource(show_spinner="🔍 Iniciando motor de OCR com Tesseract...")
def verificar_tesseract():
    try:
        versao = pytesseract.get_tesseract_version()
        return True, str(versao)
    except Exception as e:
        return False, str(e)

def extrair_texto_de_imagem(img_pil: Image.Image) -> str:
    try:
        ok, status = verificar_tesseract()
        if not ok:
            st.error(f"❌ Tesseract não está instalado ou configurado corretamente: {status}")
            return "[erro no OCR]"

        img_rgb = img_pil.convert("RGB")  # Garantir que está em RGB
        texto = pytesseract.image_to_string(img_rgb, lang='por+eng')  # Português + Inglês
        texto = texto.strip()
        return texto if texto else "[imagem sem texto legível]"
    except Exception as e:
        st.error(f"Erro ao processar imagem com OCR: {e}")
        return "[erro ao processar imagem]"
