import streamlit as st
from oraculo.auth import get_graph_token
from oraculo.scraper import get_site_id, listar_bibliotecas, listar_arquivos, baixar_arquivos

st.set_page_config(page_title="Oráculo 🔮", page_icon="📘", layout="wide")
st.title("🔮 Oráculo - Validação do Acesso ao SharePoint")

token = get_graph_token()
if not token:
    st.stop()

# Etapas do acesso
site_url = "https://carglassbr.sharepoint.com/sites/GuiaRpido"
site_id = get_site_id(token, site_url)

if site_id:
    st.success(f"📍 site_id obtido: `{site_id}`")

    drives = listar_bibliotecas(token, site_id)
    if drives:
        st.markdown("### 📚 Bibliotecas encontradas:")
        for d in drives:
            st.write(f"- {d['name']} (ID: {d['id']})")

        todos_arquivos = []
        for drive in drives:
            arquivos = listar_arquivos(token, drive["id"])
            if arquivos:
                todos_arquivos.extend(arquivos)

        st.markdown(f"### 📄 Total de arquivos detectados: {len(todos_arquivos)}")

        caminhos = baixar_arquivos(token, todos_arquivos)
        st.success(f"✅ {len(caminhos)} arquivos baixados para análise.")
    else:
        st.warning("Nenhuma biblioteca de documentos encontrada.")
else:
    st.warning("Não foi possível recuperar o site.")
