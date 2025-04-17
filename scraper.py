import os
import requests
import streamlit as st
from bs4 import BeautifulSoup

def extrair_imagens_da_pagina(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            st.error("❌ Não foi possível acessar a página do SharePoint.")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        imagens = soup.find_all("img")
        links = []

        for img in imagens:
            src = img.get("src")
            if src and "sharepoint.com" in src:
                links.append(src)

        return links
    except Exception as e:
        st.error(f"Erro ao extrair imagens: {e}")
        return []

def baixar_imagens(links, pasta="data"):
    if not os.path.exists(pasta):
        os.makedirs(pasta)

    caminhos = []
    for idx, url in enumerate(links):
        nome = f"img_{idx}.png"
        caminho = os.path.join(pasta, nome)
        try:
            r = requests.get(url)
            with open(caminho, "wb") as f:
                f.write(r.content)
            caminhos.append(caminho)
        except Exception as e:
            st.warning(f"Erro ao baixar {url}: {e}")
    return caminhos
