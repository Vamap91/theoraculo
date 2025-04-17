import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import pytesseract
from oraculo.scraper import extrair_imagens_da_pagina
from oraculo.ocr import extrair_texto_de_imagem
from openai import OpenAI
import os

# Configuração inicial
st.set_page_config(page_title="Oráculo - Extração Inteligente de Comunicados", page_icon="🔮", layout="wide")
st.title("🔮 Oráculo - Extração Inteligente de Comunicados")

# Inicializa cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Página alvo do SharePoint
url_pagina = "https://carglassbr.sharepoint.com/sites/GuiaRpido/SitePages/P%C3%A1gina%20inicial.aspx"
st.markdown(f"📎 **Lendo comunicados da página SharePoint** [Acessar site]({url_pagina})")

# Extrair imagens dos comunicados
with st.spinner("🔄 Acessando a página e localizando imagens..."):
    imagens = extrair_imagens_da_pagina(url_pagina)

if not imagens:
    st.error("❌ Não foi possível acessar a página do SharePoint.")
    st.stop()

# Mostrar imagens extraídas
st.subheader("🖼️ Comunicados encontrados:")
conteudo_extraido = []

for idx, img in enumerate(imagens):
    st.image(img, caption=f"Comunicado {idx+1}", use_column_width=True)
    texto = extrair_texto_de_imagem(img)
    conteudo_extraido.append(texto)

# Mostrar conteúdo OCR
with st.expander("🔎 Conteúdo extraído por OCR (texto bruto)", expanded=False):
    for i, texto in enumerate(conteudo_extraido):
        st.markdown(f"**Comunicado {i+1}:**")
        st.code(texto)

# Campo de pergunta
st.markdown("## 🤖 Faça uma pergunta sobre os comunicados acima:")
pergunta = st.text_input("Digite sua pergunta:")

if pergunta and conteudo_extraido:
    contexto = "\n\n---\n\n".join(conteudo_extraido)
    prompt = f"""
Você é um assistente que responde exclusivamente com base nas informações dos comunicados abaixo. 
Caso a informação não esteja presente, diga: "Não encontrei essa informação nos comunicados."

Comunicados:
{contexto}

Pergunta: {pergunta}
Resposta:
    """

    with st.spinner("🔍 Analisando com IA..."):
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente preciso que responde com base em OCR de comunicados internos."},
                {"role": "user", "content": prompt}
            ]
        )
        resposta_texto = resposta.choices[0].message.content.strip()
        st.success("💬 Resposta da IA:")
        st.write(resposta_texto)
