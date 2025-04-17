import streamlit as st
import requests
from oraculo.auth import get_graph_token

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

# Configuração da página
st.set_page_config(page_title="Oráculo 🔮", page_icon="📘", layout="wide")
st.title("🔮 Oráculo - Teste de Acesso ao SharePoint")

# 🔑 Gera token
token = get_graph_token()
if not token:
    st.stop()

# 🔍 Função auxiliar para buscar sites com o nome "Guia"
def buscar_sites_por_nome(token, keyword="Guia"):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/sites?search={keyword}"

    st.markdown("### 🔎 Buscando sites com a palavra-chave:")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        resultados = response.json().get("value", [])
        if not resultados:
            st.warning("Nenhum site encontrado com esse termo.")
            return None

        for site in resultados:
            st.markdown(f"""
            - 🧭 **Nome**: `{site['name']}`  
            - 🌐 **Web URL**: {site['webUrl']}  
            - 🆔 **Site ID**: `{site['id']}`
            """)
        
        st.success("✔️ Sites encontrados com sucesso!")
        return resultados[0]["id"]  # Usa o primeiro site como padrão
    else:
        st.error("❌ Erro ao buscar sites.")
        st.code(response.text)
        return None

# 🔁 Busca automática de site_id com base na palavra-chave "Guia"
site_id = buscar_sites_por_nome(token, keyword="Guia")

if site_id:
    st.success(f"📍 ID do site selecionado: `{site_id}`")
else:
    st.warning("⚠️ Não foi possível recuperar o site ID.")

