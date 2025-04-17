import streamlit as st
from oraculo.auth import get_graph_token
from oraculo.scraper import extrair_imagens_da_pagina, aplicar_ocr_em_imagens

st.set_page_config(page_title="Oráculo 🔮", page_icon="📘", layout="wide")
st.title("🔮 Oráculo - Extração Inteligente de Comunicados Visuais")

URL_TARGET = "https://carglassbr.sharepoint.com/sites/GuiaRpido/SitePages/P%C3%A1gina%20inicial.aspx"

st.markdown(f"### 🎯 Página-alvo: [{URL_TARGET}]({URL_TARGET})")
st.markdown("---")

with st.spinner("🔍 Extraindo imagens visíveis da página..."):
    imagens = extrair_imagens_da_pagina(URL_TARGET)

if not imagens:
    st.warning("⚠️ Nenhuma imagem encontrada na página ou erro ao acessar o SharePoint.")
    st.stop()

st.success(f"✅ {len(imagens)} imagens encontradas!")

st.markdown("---")
st.markdown("### 🧠 Resultados do OCR sobre as imagens:")

ocr_resultados = aplicar_ocr_em_imagens(imagens)

for idx, texto in enumerate(ocr_resultados):
    with st.expander(f"🖼️ Resultado OCR da Imagem {idx+1}"):
        st.markdown(f"```\n{texto}\n```")

st.markdown("---")

st.markdown("### 🤖 Pergunte algo com base nas imagens extraídas:")
pergunta = st.text_input("Digite sua pergunta:")

if pergunta:
    contexto = "\n\n".join(ocr_resultados)
    with st.spinner("🔮 Consultando IA..."):
        from openai import OpenAI
        import os
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente que responde apenas com base nas comunicações visuais extraídas de imagens."},
                {"role": "user", "content": f"Contexto:\n{contexto}\n\nPergunta: {pergunta}"}
            ],
            temperature=0.2
        )
        st.success("🧠 Resposta gerada com sucesso!")
        st.markdown(f"**Resposta:** {resposta.choices[0].message.content}")

