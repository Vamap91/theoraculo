import os
import requests
import streamlit as st

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
SITE_ID = "carglassbr.sharepoint.com,85529d0d-fc1c-4821-9aaf-da4a315706a0,12fa70b9-ebc2-46ce-90dc-896b28eeea18"

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

def listar_todos_os_arquivos(token, drive_id, caminho_pasta="/"):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/drives/{drive_id}/root:{caminho_pasta}:/children"
    response = requests.get(url, headers=headers)

    arquivos = []
    if response.status_code == 200:
        itens = response.json().get("value", [])
        for item in itens:
            if item.get("folder"):  # Se for pasta, chamar recursivamente
                nova_pasta = f"{caminho_pasta}/{item['name']}"
                arquivos += listar_todos_os_arquivos(token, drive_id, nova_pasta)
            else:
                arquivos.append(item)
    else:
        st.warning(f"Erro ao listar arquivos em {caminho_pasta}")
        st.code(response.text)
    return arquivos

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
                st.warning(f"Erro ao baixar {nome}: {e}")
    return caminhos
