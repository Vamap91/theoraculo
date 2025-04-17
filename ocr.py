import easyocr
import streamlit as st

@st.cache_resource(show_spinner="🔍 Iniciando o motor de OCR...")
def carregar_ocr():
    return easyocr.Reader(['pt'], gpu=False)

def extrair_texto_das_imagens(lista_de_caminhos):
    leitor = carregar_ocr()
    textos_extraidos = []

    for caminho in lista_de_caminhos:
        try:
            resultado = leitor.readtext(caminho, detail=0, paragraph=True)
            texto = "\n".join(resultado).strip()
            if texto:
                textos_extraidos.append(texto)
        except Exception as e:
            st.warning(f"Erro ao processar {caminho}: {e}")

    return textos_extraidos
