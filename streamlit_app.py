import streamlit as st
import os
from PIL import Image
from oraculo.auth import get_graph_token
from oraculo.scraper import listar_bibliotecas, listar_todos_os_arquivos, baixar_arquivos
from oraculo.ocr import extrair_texto_de_imagem
from openai import OpenAI

# Configuração do Streamlit
st.set_page_config(page_title="Oráculo - SharePoint com IA", page_icon="🔮", layout="wide")
st.title("🔮 Oráculo - Análise Inteligente de Documentos do SharePoint")

# 🔐 Obter token
token = get_graph_token()
if not token:
    st.error("❌ Não foi possível gerar o token de acesso.")
    st.stop()

# 📚 Listar bibliotecas (drives)
st.markdown("### 📚 Carregando bibliotecas do SharePoint...")
bibliotecas = listar_bibliotecas(token)

if not bibliotecas:
    st.warning("⚠️ Nenhuma biblioteca encontrada.")
    st.stop()

# 🧭 Selecionar uma biblioteca
nomes = [b["name"] for b in bibliotecas]
opcao = st.selectbox("Selecione uma biblioteca:", nomes)
drive = next(b for b in bibliotecas if b["name"] == opcao)

# 📄 Listar arquivos de forma profunda
st.markdown("### 🔎 Buscando todos os arquivos da biblioteca...")
arquivos = listar_todos_os_arquivos(token, drive["id"])

if not arquivos:
    st.warning("Nenhum arquivo encontrado nessa biblioteca.")
    st.stop()

st.success(f"{len(arquivos)} arquivos encontrados!")

# 📥 Baixar os arquivos
st.markdown("### 💾 Baixando arquivos válidos para OCR...")
caminhos = baixar_arquivos(token, arquivos)

if not caminhos:
    st.warning("⚠️ Nenhum arquivo com extensão suportada foi baixado.")
    st.stop()

st.success(f"✅ {len(caminhos)} arquivos baixados para a pasta `/data`.")

# 🧠 Rodar OCR nas imagens
st.markdown("### 🧠 Extraindo texto com OCR...")
conteudo_extraido = []

for caminho in caminhos:
    if caminho.lower().endswith((".png", ".jpg", ".jpeg")):
        try:
            img = Image.open(caminho)
            texto = extrair_texto_de_imagem(img)
            conteudo_extraido.append(texto)
        except Exception as e:
            st.warning(f"Erro no OCR do arquivo {caminho}: {e}")
    else:
        # Se for PDF ou DOCX (implementação futura), pula por enquanto
        continue

if not conteudo_extraido:
    st.warning("⚠️ Nenhum conteúdo extraído dos arquivos baixados.")
    st.stop()

# 🧠 Montar prompt com IA
st.markdown("## 🤖 Faça uma pergunta sobre os comunicados extraídos:")
pergunta = st.text_input("Digite sua pergunta:")

if pergunta:
    contexto = "\n\n---\n\n".join(conteudo_extraido)
    prompt = f"""
Você é um assistente que responde com base em comunicados extraídos de documentos visuais via OCR.

Caso a informação não esteja presente, diga: "Não encontrei essa informação nos documentos fornecidos."

Comunicados:
{contexto}

Pergunta: {pergunta}
Resposta:
    """

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    with st.spinner("Consultando o Oráculo..."):
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você responde exclusivamente com base nos textos extraídos via OCR."},
                {"role": "user", "content": prompt}
            ]
        )
        conteudo = resposta.choices[0].message.content.strip()
        st.success("💬 Resposta da IA:")
        st.markdown(conteudo)
