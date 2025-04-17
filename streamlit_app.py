import streamlit as st
from oraculo.auth import get_graph_token

st.set_page_config(page_title="Oráculo 🔮", page_icon="📘", layout="wide")
st.title("🔮 Oráculo de Conhecimento Interno")

st.write("Conectando-se ao SharePoint para extrair insights com IA...")

# Autenticação com Graph API
token = get_graph_token()
if token:
    st.success("✅ Token obtido com sucesso!")
    st.session_state["access_token"] = token
else:
    st.stop()

