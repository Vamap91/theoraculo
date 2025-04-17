import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
import pytesseract

def extrair_imagens_da_pagina(url, pasta_destino="data"):
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[ERRO] Falha ao acessar a página: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    imagens = soup.find_all("img")

    caminhos_salvos = []

    for i, img_tag in enumerate(imagens):
        src = img_tag.get("src")
        if not src:
            continue

        img_url = urljoin(url, src)

        try:
            img_data = requests.get(img_url).content
            img = Image.open(BytesIO(img_data)).convert("RGB")

            caminho = os.path.join(pasta_destino, f"imagem_{i+1}.jpg")
            img.save(caminho)
            caminhos_salvos.append(caminho)
        except Exception as e:
            print(f"[ERRO] Erro ao baixar ou salvar imagem {img_url}: {e}")
            continue

    return caminhos_salvos

def aplicar_ocr_em_imagens(lista_caminhos):
    resultados = []
    for caminho in lista_caminhos:
        try:
            img = Image.open(caminho)
            texto = pytesseract.image_to_string(img, lang="por")
            resultados.append(texto.strip())
        except Exception as e:
            resultados.append(f"[ERRO] ao processar {caminho}: {e}")
    return resultados
