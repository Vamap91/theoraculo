import streamlit as st
import numpy as np
from openai import OpenAI

@st.cache_resource(show_spinner="🔌 Conectando com OpenAI para gerar embeddings...")
def carregar_cliente_openai():
    api_key = st.secrets["OPENAI_API_KEY"]
    return OpenAI(api_key=api_key)

def gerar_embeddings(lista_de_textos):
    client = carregar_cliente_openai()

    try:
        resposta = client.embeddings.create(
            model="text-embedding-ada-002",
            input=lista_de_textos
        )
        return np.array([item.embedding for item in resposta.data])
    except Exception as e:
        st.error(f"Erro ao gerar embeddings: {e}")
        return []
