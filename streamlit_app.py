import streamlit as st
from oraculo.auth import get_graph_token
from oraculo.scraper import listar_bibliotecas, listar_arquivos, baixar_arquivos

GRAPH_SITE_ID = "carglassbr.sharepoint.com,85529d0d-fc1c-4821-9aaf-da4a315706a0,12fa70b9-ebc2-46ce-90dc-896b28eeea18"

st.set_page_config(page_title="Oráculo 🔮", page_icon="📘", layout="wide")
st.title("🔮 Oráculo - Extração Inteligente de Arquivos do SharePoint")

token = get_graph_token()
if not token:
    st.stop()

st.markdown(f"### 🧠 Usando site ID conhecido:\n`{GRAPH_SITE_ID}`")

# Listar bibliotecas (drives)
drives = listar_bibliotecas(token, GRAPH_SITE_ID)
if not drives:
    st.warning("⚠️ Nenhuma biblioteca foi encontrada no site.")
    st.stop()

st.markdown("## 📁 Bibliotecas de Documentos Encontradas:")
for d in drives:
    st.write(f"- {d['name']} (ID: {d['id']})")

# Buscar arquivos em todas as bibliotecas
todos_arquivos = []
for drive in drives:
    arquivos = listar_arquivos(token, drive["id"])
    if arquivos:
        todos_arquivos.extend(arquivos)

st.markdown(f"### 📄 Total de arquivos detectados: {len(todos_arquivos)}")

# Baixar arquivos para a pasta local
if todos_arquivos:
    caminhos = baixar_arquivos(token, todos_arquivos)
    st.success(f"✅ {len(caminhos)} arquivos baixados para a pasta `data/` com sucesso!")
else:
    st.warning("Nenhum arquivo relevante encontrado para download.")
