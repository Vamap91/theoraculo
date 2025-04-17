import streamlit as st
from oraculo.auth import get_graph_token
from oraculo.scraper import extrair_imagens_da_pagina, baixar_imagens
from oraculo.ocr import extrair_texto_das_imagens
from oraculo.embeddings import gerar_embeddings

st.set_page_config(page_title="Oráculo 🔮", page_icon="📘", layout="wide")
st.title("🔮 Oráculo - Extração Inteligente de Comunicados")

# 1. Autenticação (placeholder para Graph API futura)
token = get_graph_token()
if not token:
    st.stop()

# 2. URL da página
url_pagina = "https://carglassbr.sharepoint.com/sites/GuiaRpido/SitePages/P%C3%A1gina%20inicial.aspx"
st.subheader("🔗 Lendo comunicados da página SharePoint")
st.write(f"Página-alvo: {url_pagina}")

# 3. Extrair links de imagens da página
links = extrair_imagens_da_pagina(url_pagina)

if not links:
    st.warning("Nenhuma imagem encontrada na página.")
    st.stop()

st.success(f"{len(links)} imagens encontradas na página.")
st.markdown("---")

# 4. Baixar imagens
caminhos = baixar_imagens(links)
if not caminhos:
    st.warning("❌ Falha ao baixar imagens.")
    st.stop()

# 5. Rodar OCR nas imagens
st.markdown("### 🧠 Rodando OCR nas imagens...")
textos = extrair_texto_das_imagens(caminhos)

if not textos:
    st.warning("Nenhum texto foi extraído via OCR.")
    st.stop()

# 6. Mostrar resultados do OCR
st.markdown("### 📃 Textos extraídos:")
for i, t in enumerate(textos):
    st.markdown(f"**Imagem {i+1}:**")
    st.code(t[:1000])  # Exibe até 1000 caracteres por trecho

# 7. Gerar embeddings com OpenAI
st.markdown("### 🔮 Gerando vetores semânticos (embeddings)...")
vetores = gerar_embeddings(textos)

if vetores is not None and len(vetores) > 0:
    st.success(f"✅ Embeddings gerados para {len(vetores)} blocos.")
    st.session_state["chunks"] = textos
    st.session_state["embeddings"] = vetores
else:
    st.warning("❌ Não foi possível gerar embeddings para os textos.")
