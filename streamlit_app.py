"""
ORÁCULO - Análise Inteligente de Documentos do SharePoint
"""

import os
import tempfile
import streamlit as st
import requests
import io
from PIL import Image
import pytesseract
import pdf2image
from openai import OpenAI
import time

# Configuração da página Streamlit
st.set_page_config(
    page_title="Oráculo - SharePoint com IA", 
    page_icon="🔮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
SITE_ID = "carglassbr.sharepoint.com,7d0ecc3f-b6c8-411d-8ae4-6d5679a38ca8,e53fc2d9-95b5-4675-813d-769b7a737286"
DATA_DIR = "data"

# Verifica e cria o diretório para armazenar os arquivos, se não existir
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Título e descrição
st.title("🔮 Oráculo - Análise Inteligente de Documentos do SharePoint")
st.markdown("""
Este sistema acessa bibliotecas do SharePoint, extrai texto de documentos visuais e 
permite consultas em linguagem natural usando IA.
""")

# Configuração do OCR e caminhos
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Configuração do OCR
    st.subheader("Configuração do OCR")
    ocr_language = st.selectbox(
        "Idioma principal para OCR:",
        options=["por", "por+eng", "eng"],
        index=1,
        help="Selecione o idioma principal dos documentos"
    )
    
    # Configuração do modelo de IA
    st.subheader("Configuração da IA")
    ai_model = st.selectbox(
        "Modelo OpenAI:",
        options=["gpt-3.5-turbo", "gpt-4"],
        index=0
    )
    
    st.divider()
    
    # Informações do projeto
    st.markdown("### 📋 Sobre o Projeto")
    st.markdown("""
    **Oráculo** é uma ferramenta que:
    - Conecta ao SharePoint via Microsoft Graph API
    - Baixa documentos visuais (imagens e PDFs)
    - Extrai texto via OCR
    - Responde perguntas usando IA
    """)
    
# Cache para o token
@st.cache_resource(ttl=3500)  # Quase 1 hora, tokens geralmente expiram em 1h
def get_graph_token():
    """Obtém token de autenticação para a Microsoft Graph API"""
    try:
        tenant_id = st.secrets["TENANT_ID"]
        client_id = st.secrets["CLIENT_ID"]
        client_secret = st.secrets["CLIENT_SECRET"]
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": client_id,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }

        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            st.error(f"Erro ao gerar token: {response.status_code}")
            st.code(response.text)
            return None
    except Exception as e:
        st.error(f"Erro na autenticação: {str(e)}")
        return None

def listar_bibliotecas(token):
    """Lista todas as bibliotecas do SharePoint"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/sites/{SITE_ID}/drives"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("value", [])
        else:
            st.error(f"❌ Erro ao listar bibliotecas: {response.status_code}")
            st.code(response.text)
            return []
    except Exception as e:
        st.error(f"Erro ao listar bibliotecas: {str(e)}")
        return []

def listar_todos_os_arquivos(token, drive_id, caminho_pasta="/", progress_bar=None, limite=None):
    """Lista todos os arquivos em uma biblioteca, incluindo subpastas"""
    headers = {"Authorization": f"Bearer {token}"}
    if caminho_pasta == "/":
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root/children"
    else:
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root:{caminho_pasta}:/children"

    arquivos = []
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            itens = response.json().get("value", [])
            
            # Atualiza a barra de progresso, se fornecida
            if progress_bar:
                progress_bar.progress(0.1, text="Iniciando busca...")
            
            for i, item in enumerate(itens):
                # Aplica o limite, se especificado
                if limite and len(arquivos) >= limite:
                    break
                    
                if item.get("folder"):
                    nova_pasta = f"{caminho_pasta}/{item['name']}".replace("//", "/")
                    sub_arquivos = listar_todos_os_arquivos(token, drive_id, nova_pasta, limite=limite)
                    arquivos.extend(sub_arquivos)
                else:
                    arquivos.append(item)
                
                # Atualiza a barra de progresso
                if progress_bar:
                    progress = min(0.1 + 0.8 * (i / len(itens)), 0.9)
                    progress_bar.progress(progress, text=f"Processando pasta {caminho_pasta}...")
        else:
            st.warning(f"Erro ao listar arquivos em {caminho_pasta}: {response.status_code}")
            if response.status_code != 404:  # Ignora erros 404 (pasta não encontrada)
                st.code(response.text)
    except Exception as e:
        st.error(f"Erro ao listar arquivos: {str(e)}")
    
    # Finaliza a barra de progresso
    if progress_bar and caminho_pasta == "/":
        progress_bar.progress(1.0, text="Busca concluída!")
        time.sleep(0.5)
        progress_bar.empty()
    
    return arquivos

def baixar_arquivo(token, download_url, nome_arquivo, pasta_destino=DATA_DIR):
    """Baixa um único arquivo e retorna o caminho local"""
    headers = {"Authorization": f"Bearer {token}"}
    caminho_local = os.path.join(pasta_destino, nome_arquivo)
    
    try:
        response = requests.get(download_url, headers=headers)
        if response.status_code == 200:
            # Salva o arquivo localmente
            with open(caminho_local, "wb") as f:
                f.write(response.content)
            return caminho_local, response.content
        else:
            st.warning(f"Erro ao baixar {nome_arquivo}: {response.status_code}")
            return None, None
    except Exception as e:
        st.warning(f"Erro ao baixar {nome_arquivo}: {str(e)}")
        return None, None

def extrair_texto_de_imagem(img_data_or_path):
    """Extrai texto de uma imagem usando OCR"""
    try:
        # Se for um caminho para arquivo
        if isinstance(img_data_or_path, str):
            if not os.path.exists(img_data_or_path):
                return ""
            img = Image.open(img_data_or_path)
        # Se for conteúdo binário
        elif isinstance(img_data_or_path, bytes):
            img = Image.open(io.BytesIO(img_data_or_path))
        # Se já for um objeto PIL Image
        elif isinstance(img_data_or_path, Image.Image):
            img = img_data_or_path
        else:
            return ""
        
        # Aplica pré-processamento para melhorar a qualidade do OCR
        # Converte para RGB se necessário (para imagens PNG com transparência)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        # Extrai o texto usando pytesseract
        texto = pytesseract.image_to_string(img, lang=ocr_language)
        return texto.strip()
    except Exception as e:
        st.error(f"Erro ao processar imagem com OCR: {str(e)}")
        return ""

def extrair_texto_de_pdf(pdf_data_or_path):
    """Extrai texto de um PDF usando OCR em cada página"""
    try:
        # Se for um caminho para arquivo
        if isinstance(pdf_data_or_path, str):
            if not os.path.exists(pdf_data_or_path):
                return ""
            with open(pdf_data_or_path, 'rb') as f:
                pdf_data = f.read()
        # Se for conteúdo binário
        elif isinstance(pdf_data_or_path, bytes):
            pdf_data = pdf_data_or_path
        else:
            return ""
        
        # Converte PDF para imagens
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_data)
            temp_pdf_path = temp_pdf.name
        
        # Extrai imagens de cada página do PDF
        imagens = pdf2image.convert_from_path(temp_pdf_path, dpi=300)
        
        # Remove o arquivo temporário
        os.unlink(temp_pdf_path)
        
        # Extrai texto de cada página
        textos = []
        for img in imagens:
            texto_pagina = extrair_texto_de_imagem(img)
            if texto_pagina:
                textos.append(texto_pagina)
        
        return "\n\n".join(textos)
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return ""

def extrair_texto_de_arquivo(caminho_ou_conteudo, nome_arquivo=None):
    """Extrai texto de um arquivo baseado em sua extensão"""
    # Determina a extensão
    if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
        nome = caminho_ou_conteudo.lower()
    else:
        nome = nome_arquivo.lower() if nome_arquivo else ""
    
    # Extrai texto baseado no tipo de arquivo
    if nome.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        return extrair_texto_de_imagem(caminho_ou_conteudo)
    elif nome.endswith('.pdf'):
        return extrair_texto_de_pdf(caminho_ou_conteudo)
    elif nome.endswith('.txt'):
        # Se for um caminho para arquivo de texto
        if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
            with open(caminho_ou_conteudo, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        # Se for conteúdo binário de um arquivo de texto
        elif isinstance(caminho_ou_conteudo, bytes):
            return caminho_ou_conteudo.decode('utf-8', errors='ignore')
    
    return ""  # Retorna string vazia para tipos não suportados

def processar_pergunta(pergunta, conteudo_extraido, modelo_ia="gpt-3.5-turbo"):
    """Processa uma pergunta usando a API da OpenAI"""
    try:
        contexto = "\n\n---\n\n".join(conteudo_extraido)
        
        prompt = f"""
Você é um assistente inteligente especializado em analisar e responder com base em comunicados e documentos operacionais.

CONTEXTO DOS DOCUMENTOS:
{contexto}

INSTRUÇÕES:
1. Baseie sua resposta EXCLUSIVAMENTE nas informações contidas nos documentos fornecidos.
2. Se a informação não estiver presente nos documentos, responda claramente: "Não encontrei essa informação nos documentos fornecidos."
3. Se os documentos contiverem informações parciais, informe quais partes você encontrou e quais estão faltando.
4. Forneça a resposta de forma clara, concisa e estruturada.
5. Quando relevante, indique de qual documento ou seção a informação foi extraída.

PERGUNTA DO USUÁRIO: {pergunta}
"""

        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        resposta = client.chat.completions.create(
            model=modelo_ia,
            messages=[
                {"role": "system", "content": "Você é um assistente especializado que responde apenas com base nos documentos fornecidos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Menor temperatura para respostas mais precisas
        )
        
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Erro ao processar pergunta com IA: {str(e)}")
        return f"Ocorreu um erro ao processar sua pergunta: {str(e)}"

# Início da aplicação principal
token = get_graph_token()
if not token:
    st.error("❌ Não foi possível gerar o token de acesso ao SharePoint.")
    st.info("Verifique se as credenciais estão configuradas corretamente nos secrets do Streamlit.")
    st.stop()

# Carrega bibliotecas do SharePoint
with st.expander("📚 Bibliotecas do SharePoint", expanded=True):
    st.info("Carregando bibliotecas do SharePoint...")
    bibliotecas = listar_bibliotecas(token)
    
    if not bibliotecas:
        st.warning("⚠️ Nenhuma biblioteca encontrada.")
        st.stop()
    
    # Mostra as bibliotecas disponíveis
    nomes_bibliotecas = [b["name"] for b in bibliotecas]
    biblioteca_selecionada = st.selectbox("Selecione uma biblioteca:", nomes_bibliotecas)
    
    # Encontra o drive_id da biblioteca selecionada
    drive = next(b for b in bibliotecas if b["name"] == biblioteca_selecionada)
    drive_id = drive["id"]
    
    # Opção para limitar o número de arquivos
    col1, col2 = st.columns(2)
    with col1:
        limitar_arquivos = st.checkbox("Limitar número de arquivos", value=True)
    with col2:
        if limitar_arquivos:
            limite_arquivos = st.number_input("Número máximo de arquivos:", min_value=1, max_value=100, value=10)
        else:
            limite_arquivos = None
    
    # Botão para buscar arquivos
    if st.button("🔍 Buscar Arquivos na Biblioteca"):
        with st.spinner("Buscando todos os arquivos da biblioteca..."):
            progress_bar = st.progress(0, text="Iniciando busca...")
            arquivos = listar_todos_os_arquivos(token, drive_id, progress_bar=progress_bar, limite=limite_arquivos)
            
            if not arquivos:
                st.warning("⚠️ Nenhum arquivo encontrado nessa biblioteca.")
                st.stop()
            
            # Filtra apenas extensões suportadas
            extensoes_validas = [".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".txt"]
            arquivos_validos = [
                arq for arq in arquivos 
                if any(arq.get("name", "").lower().endswith(ext) for ext in extensoes_validas)
            ]
            
            # Mostra quantidade de arquivos encontrados
            total_arquivos = len(arquivos)
            total_validos = len(arquivos_validos)
            
            if total_validos == 0:
                st.warning(f"⚠️ Foram encontrados {total_arquivos} arquivos, mas nenhum com formato suportado para OCR.")
                st.info("Formatos suportados: " + ", ".join(extensoes_validas))
                st.stop()
            
            st.success(f"✅ Encontrados {total_arquivos} arquivos, sendo {total_validos} com formato suportado para OCR.")
            
            # Salva na session_state para não perder ao recarregar
            st.session_state['arquivos_validos'] = arquivos_validos
            st.session_state['biblioteca_selecionada'] = biblioteca_selecionada
            st.session_state['drive_id'] = drive_id

# Processamento dos arquivos encontrados
if 'arquivos_validos' in st.session_state and st.session_state['arquivos_validos']:
    arquivos_validos = st.session_state['arquivos_validos']
    
    with st.expander("💾 Arquivos para Processamento", expanded=True):
        st.write(f"Biblioteca: **{st.session_state['biblioteca_selecionada']}**")
        
        # Exibe a lista de arquivos e permite seleção
        nomes_arquivos = [arq.get("name", "Sem nome") for arq in arquivos_validos]
        arquivos_selecionados = st.multiselect(
            "Selecione os arquivos para processamento:",
            options=nomes_arquivos,
            default=nomes_arquivos[:min(5, len(nomes_arquivos))]  # Seleciona os 5 primeiros por padrão
        )
        
        if not arquivos_selecionados:
            st.warning("⚠️ Selecione pelo menos um arquivo para processamento.")
        else:
            # Botão para iniciar o processamento
            if st.button("📥 Processar Arquivos Selecionados"):
                conteudo_extraido = []
                
                with st.spinner(f"Processando {len(arquivos_selecionados)} arquivos..."):
                    # Cria uma barra de progresso
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Processa cada arquivo selecionado
                    for idx, nome in enumerate(arquivos_selecionados):
                        # Atualiza status
                        progresso = idx / len(arquivos_selecionados)
                        progress_bar.progress(progresso)
                        status_text.text(f"Processando {nome}... ({idx+1}/{len(arquivos_selecionados)})")
                        
                        # Encontra o arquivo na lista de arquivos válidos
                        arquivo = next(a for a in arquivos_validos if a.get("name") == nome)
                        download_url = arquivo.get("@microsoft.graph.downloadUrl")
                        
                        if download_url:
                            # Baixa o arquivo
                            caminho_local, conteudo_binario = baixar_arquivo(token, download_url, nome)
                            
                            if caminho_local:
                                # Tenta extrair texto do arquivo
                                texto = extrair_texto_de_arquivo(conteudo_binario, nome)
                                
                                if texto:
                                    # Adiciona à lista de conteúdos extraídos
                                    conteudo_extraido.append(f"--- Documento: {nome} ---\n{texto}")
                    
                    # Finaliza o progresso
                    progress_bar.progress(1.0)
                    time.sleep(0.5)
                    progress_bar.empty()
                    status_text.empty()
                
                # Verifica se algum conteúdo foi extraído
                if not conteudo_extraido:
                    st.warning("⚠️ Não foi possível extrair texto de nenhum dos arquivos selecionados.")
                    st.info("Verifique se os arquivos contêm texto legível para OCR ou se o Tesseract está configurado corretamente.")
                else:
                    st.success(f"✅ Texto extraído com sucesso de {len(conteudo_extraido)} arquivo(s)!")
                    
                    # Mostra amostra do texto extraído (primeiros 500 caracteres)
                    with st.expander("📝 Amostra do Texto Extraído"):
                        for idx, texto in enumerate(conteudo_extraido[:3]):  # Mostra apenas os 3 primeiros
                            st.markdown(f"**Documento {idx+1}:**")
                            st.text(texto[:500] + "..." if len(texto) > 500 else texto)
                    
                    # Salva na session_state
                    st.session_state['conteudo_extraido'] = conteudo_extraido

# Interface para perguntas e respostas
if 'conteudo_extraido' in st.session_state and st.session_state['conteudo_extraido']:
    st.header("🤖 Consulte o Oráculo")
    st.markdown("Faça perguntas sobre os documentos e o Oráculo responderá com base no conteúdo extraído.")
    
    # Campo para a pergunta
    pergunta = st.text_area("Digite sua pergunta:", height=100)
    
    # Botão para processar a pergunta
    if pergunta and st.button("🔮 Consultar o Oráculo"):
        with st.spinner("O Oráculo está analisando sua pergunta..."):
            resposta = processar_pergunta(
                pergunta, 
                st.session_state['conteudo_extraido'],
                modelo_ia=ai_model
            )
            
            # Exibe a resposta em um componente especial
            st.markdown("### 💬 Resposta do Oráculo:")
            st.markdown(
                f"""<div style="background-color: #f0f8ff; padding: 20px; 
                border-radius: 10px; border-left: 5px solid #4682b4;">
                {resposta}
                </div>""", 
                unsafe_allow_html=True
            )
            
            # Adiciona na sessão
            if 'historico' not in st.session_state:
                st.session_state['historico'] = []
            
            # Adiciona ao histórico (limitado aos últimos 5)
            st.session_state['historico'].insert(
                0, {"pergunta": pergunta, "resposta": resposta}
            )
            if len(st.session_state['historico']) > 5:
                st.session_state['historico'] = st.session_state['historico'][:5]

# Mostra histórico de perguntas, se existir
if 'historico' in st.session_state and st.session_state['historico']:
    with st.expander("📜 Histórico de Consultas", expanded=False):
        for idx, item in enumerate(st.session_state['historico']):
            st.markdown(f"**Pergunta {idx+1}:** {item['pergunta']}")
            st.markdown(
                f"""<div style="background-color: #f5f5f5; padding: 10px; 
                border-radius: 5px; margin-bottom: 15px; font-size: 0.9em;">
                {item['resposta']}
                </div>""", 
                unsafe_allow_html=True
            )
