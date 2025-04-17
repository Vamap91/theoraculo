import streamlit as st
from oraculo.auth import get_graph_token
from oraculo.scraper import extrair_imagens_da_pagina, baixar_imagens
from oraculo.ocr import extrair_texto_das_imagens

st.set_page_config(page_title="Oráculo 🔮", page_icon="📘", layout="wide")
st.title("🔮 Oráculo - Extração de Conhecimento Internos")

# 🔐 Autenticação com Microsoft Graph (futuramente para HTML privado)
token = get_graph_token()
if not token:
    st.stop()

# 📎 URL da página de comunicados
url_pagina = "https://carglassbr.sharepoint.com/sites/GuiaRpido/SitePages/P%C3%A1gina%20inicial.aspx"

st.markdown("## 🔗 Lendo a página pública do SharePoint")
st.write(f"Página: {url_pagina}")

# 🔍 Etapa 1: Extrair imagens da página HTML
links = extrair_imagens_da_pagina(url_pagina)

if not links:
    st.warning("Nenhuma imagem com link SharePoint encontrada na página.")
    st.stop()

st.success(f"{len(links)} imagens encontradas!")
st.markdown("---")

# 💾 Etapa 2: Baixar as imagens localmente
st.markdown("### 📥 Baixando imagens...")
caminhos = baixar_imagens(links)

if not caminhos:
    st.warning("Não foi possível baixar as imagens.")
    st.stop()

# 🧠 Etapa 3: Rodar OCR nas imagens baixadas
st.markdown("### 🧠 Rodando OCR com IA")
textos = extrair_texto_das_imagens(caminhos)

if textos:
    st.markdown("### 📃 Resultados da Leitura por Imagem:")
    for i, texto in enumerate(textos):
        st.markdown(f"**Imagem {i+1}:**")
        st.code(texto[:1000])  # Mostra só os primeiros 1000 caracteres
else:
    st.warning("OCR não retornou nenhum texto legível.")
