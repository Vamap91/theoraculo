# oraculo/scraper.py

import requests
import streamlit as st

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

def get_site_id(token, site_url):
    headers = {"Authorization": f"Bearer {token}"}
    domain = site_url.split("/sites/")[0].replace("https://", "")
    site_path = site_url.split("/sites/")[1]

    url = f"{GRAPH_ROOT}/sites/{domain}:/sites/{site_path}"
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        return resp.json()["id"]
    else:
        st.error(f"Erro ao buscar site ID: {resp.text}")
        return None

def list_drive_items(token, site_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/sites/{site_id}/drive/root/children"
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        return resp.json().get("value", [])
    else:
        st.error(f"Erro ao listar arquivos: {resp.text}")
        return []
