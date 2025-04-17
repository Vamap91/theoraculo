import os
import requests
import streamlit as st

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

def get_site_id(token, site_url="https://carglassbr.sharepoint.com/sites/GuiaRpido"):
    headers = {"Authorization": f"Bearer {token}"}
    site_path = site_url.replace("https://", "").split("/", 1)[1]
    domain = "carglassbr.sharepoint.com"
    url = f"{GRAPH_ROOT}/sites/{domain}:/sites/{site_path}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["id"]
    else:
        st.error("❌ Erro ao obter site_id")
        st.code(response.text)
        return None

def listar_bibliotecas(token, site_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/sites/{site_id}/drives"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        st.error("❌ Erro ao listar drives")
        st.code(response.text)
        return []

def listar_arquivos(token, drive_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/drives/{drive_id}/root/children"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        return []

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
