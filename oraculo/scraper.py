import os
import requests
import streamlit as st

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

# Novo site_id validado pelo time de segurança
SITE_ID = "carglassbr.sharepoint.com,7d0ecc3f-b6c8-411d-8ae4-6d5679a38ca8,e53fc2d9-95b5-4675-813d-769b7a737286"

# 🔍 Listar bibliotecas (drives) disponíveis no site
def listar_bibliotecas(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/sites/{SITE_ID}/drives"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        st.error("❌ Erro ao listar bibliotecas")
        st.code(response.text)
        return []

# 📂 Listar arquivos recursivamente (com correção do root/children)
def listar_todos_os_arquivos(token, drive_id, caminho_pasta="/"):
    headers = {"Authorization": f"Bearer {token}"}

    # Correção do erro "Resource not found for segment 'root:'"
    if caminho_pasta == "/":
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root/children"
    else:
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root:{caminho_pasta}:/children"

    response = requests.get(url, headers=headers)

    arquivos = []
    if response.status_code == 200:
        itens = response.json().get("value", [])
        for item in itens:
            if item.get("folder"):  # 📁 Se for pasta, entra nela
                nova_pasta = f"{caminho_pasta}/{item['name']}".replace("//", "/")
                arquivos += listar_todos_os_arquivos(token, drive_id, nova_pasta)
            else:
                arquivos.append(item)
    else:
        st.warning(f"⚠️ Erro ao listar arquivos em {caminho_pasta}")
        st.code(response.text)
    return arquivos

# 💾 Baixar arquivos válidos (com extensão permitida)
def baixar_arquivos(token, arquivos, pasta="data", extensoes_validas=None):
    if extensoes_validas is None:
        extensoes_validas = [".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".txt"]

    headers = {"Authorization": f"Bearer {token}"}
    if not os.path.exists(pasta):
        os.makedirs(pasta)

    caminhos = []
    for arq in arquivos:
        nome = arq.get("name", "")
        link = arq.get("@microsoft.graph.downloadUrl")

        if any(nome.lower().endswith(ext) for ext in extensoes_validas) and link:
            local = os.path.join(pasta, nome)
            try:
                r = requests.get(link, headers=headers)
                with open(local, "wb") as f:
                    f.write(r.content)
                caminhos.append(local)
            except Exception as e:
                st.warning(f"⚠️ Erro ao baixar {nome}: {e}")
    return caminhos

