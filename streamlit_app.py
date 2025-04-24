import os
import tempfile
import platform
import streamlit as st
import requests
import io
import traceback
import json
import time
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import numpy as np
from typing import List, Dict, Optional, Tuple, Any, Union

# Importações para Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    selenium_disponivel = True
except ImportError:
    selenium_disponivel = False
    st.warning("Selenium não está instalado. A navegação avançada não estará disponível.")

# Configuração para o Poppler (necessário para PDFs) - SOLUÇÃO DO ERRO
if platform.system() == "Windows":
    # Adiciona alguns caminhos comuns do Poppler ao PATH
    possible_poppler_paths = [
        r"C:\poppler\bin",
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files (x86)\poppler\bin",
        r"C:\Users\Administrator\AppData\Local\Programs\poppler\bin"
    ]
    
    for path in possible_poppler_paths:
        if os.path.exists(path):
            os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
            break

# Tenta importar o módulo PyMuPDF primeiro (prioritário)
try:
    import fitz  # PyMuPDF
    pdf_processor = "pymupdf"
except ImportError:
    pdf_processor = None
    st.warning("PyMuPDF não está instalado. Tentando alternativa...")

# Se PyMuPDF falhar, tenta usar pdf2image
if pdf_processor is None:
    try:
        import pdf2image
        pdf_processor = "pdf2image"
    except ImportError:
        pdf_processor = None
        st.error("Nenhum processador de PDF disponível. Instale pymupdf ou pdf2image.")

# Tenta importar python-magic para detecção de tipos de arquivo
try:
    import magic
    has_magic = True
except ImportError:
    has_magic = False

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
SHAREPOINT_URL = "https://carglassbr.sharepoint.com/sites/GuiaRapido"

# Verifica e cria o diretório para armazenar os arquivos, se não existir
if not os.path.exists(DATA_DIR) :
    os.makedirs(DATA_DIR)

# Título e descrição
st.title("🔮 Oráculo - Análise Inteligente de Documentos do SharePoint")
st.markdown("""
Este sistema acessa bibliotecas do SharePoint, extrai texto de documentos visuais e 
permite consultas em linguagem natural usando IA.
""")

# Botão para limpar cache e reiniciar
if st.button("🧹 Limpar cache e reiniciar"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

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
    
    # Configuração de pré-processamento de imagem
    st.subheader("Pré-processamento de imagem")
    use_preprocessing = st.checkbox("Aplicar pré-processamento de imagem", value=True,
                                    help="Melhora a qualidade do OCR em imagens")
    
    # Exibe opções avançadas se o pré-processamento estiver ativado
    if use_preprocessing:
        preprocessing_options = st.multiselect(
            "Técnicas de pré-processamento:",
            options=["Aumentar contraste", "Escala de cinza", "Nitidez", "Remover ruído"],
            default=["Aumentar contraste", "Escala de cinza", "Nitidez"]
        )
    
    # Configuração do modelo de IA
    st.subheader("Configuração da IA")
    ai_model = st.selectbox(
        "Modelo OpenAI:",
        options=["gpt-3.5-turbo", "gpt-4"],
        index=0
    )
    
    # Configuração do método de acesso ao SharePoint
    st.subheader("Método de Acesso ao SharePoint")
    metodo_acesso = st.radio(
        "Método de acesso:",
        options=["API Graph (Padrão)", "Navegação Avançada (Selenium)"],
        index=0,
        help="Escolha como acessar os documentos do SharePoint"
    )
    
    if metodo_acesso == "Navegação Avançada (Selenium)" and not selenium_disponivel:
        st.error("❌ Selenium não está instalado. Instale com: pip install selenium webdriver-manager")
    
    st.divider()
    
    # Verifica o status do sistema
    st.subheader("Status do Sistema")
    
    # Verifica Tesseract OCR
    try:
        tesseract_version = pytesseract.get_tesseract_version()
        st.success(f"✅ Tesseract OCR v{tesseract_version} instalado")
    except:
        st.error("❌ Tesseract OCR não encontrado")
    
    # Verifica processador de PDF
    if pdf_processor == "pymupdf":
        st.success("✅ PyMuPDF está sendo usado para PDFs")
    elif pdf_processor == "pdf2image":
        try:
            pdf2image.pdfinfo_from_bytes(b"%PDF-1.0\n1 0 obj<</Pages 2 0 R>>/endobj/trailer<</Root 1 0 R>>")
            st.success("✅ Poppler está instalado corretamente")
        except Exception as e:
            st.error(f"⚠️ Poppler não está configurado corretamente")
    else:
        st.error("❌ Nenhum processador de PDF disponível")
    
    # Verifica Selenium
    if selenium_disponivel:
        st.success("✅ Selenium está disponível para navegação avançada")
    else:
        st.warning("⚠️ Selenium não está instalado (navegação avançada indisponível)")
    
    # Informações do projeto
    st.markdown("### 📋 Sobre o Projeto")
    st.markdown("""
    **Oráculo** é uma ferramenta que:
    - Conecta ao SharePoint via Microsoft Graph API
    - Baixa documentos visuais (principalmente imagens)
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

        response = requests.post(url, headers=headers, data=data, timeout=30) 
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            st.error(f"Erro ao gerar token de acesso: {response.status_code}")
            if st.checkbox("Mostrar detalhes do erro", value=False):
                st.code(response.text)
            return None
            
    except KeyError as e:
        st.error(f"Erro de configuração: chave não encontrada em st.secrets: {str(e)}")
        st.info("Verifique se as credenciais de autenticação estão configuradas corretamente.")
        return None
        
    except Exception as e:
        st.error(f"Erro durante a autenticação: {str(e)}")
        return None

def listar_bibliotecas(token):
    """Lista todas as bibliotecas do SharePoint"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/sites/{SITE_ID}/drives"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json().get("value", [])
        else:
            st.error(f"❌ Erro ao listar bibliotecas: {response.status_code}")
            st.code(response.text)
            return []
    except Exception as e:
        st.error(f"Erro ao listar bibliotecas: {str(e)}")
        return []

def listar_pastas(token, drive_id, folder_path="/"):
    """
    Lista apenas as pastas em um caminho específico.
    """
    headers = {"Authorization": f"Bearer {token}"}
    
    # Determine a URL correta com base no caminho da pasta
    if folder_path == "/":
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root/children"
    else:
        # Certifique-se de que o caminho da pasta não comece com '/'
        if folder_path.startswith("/"):
            folder_path = folder_path[1:]
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root:/{folder_path}:/children"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Filtra apenas itens que são pastas
            items = response.json().get("value", [])
            folders = []
            
            for item in items:
                if item.get("folder"):
                    # Adiciona informação de nível hierárquico à pasta
                    nivel = folder_path.count('/') + 1
                    item['_nivel_hierarquico'] = nivel
                    item['_caminho_pasta'] = folder_path
                    folders.append(item)
            
            return folders
        else:
            st.warning(f"Erro ao listar pastas em {folder_path}: {response.status_code}")
            return []
    except Exception as e:
        st.warning(f"Erro ao listar pastas em {folder_path}: {str(e)}")
        return []

def listar_arquivos(token, drive_id, folder_path="/", extensoes_validas=None):
    """
    Lista apenas os arquivos (não pastas) em um caminho específico.
    """
    headers = {"Authorization": f"Bearer {token}"}
    
    # Define extensões válidas padrão se não fornecidas
    if extensoes_validas is None:
        extensoes_validas = [".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".txt"]
    
    # Determine a URL correta com base no caminho da pasta
    if folder_path == "/":
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root/children"
    else:
        # Certifique-se de que o caminho da pasta não comece com '/'
        if folder_path.startswith("/"):
            folder_path = folder_path[1:]
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root:/{folder_path}:/children"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Filtra apenas itens que NÃO são pastas e têm extensões válidas
            items = response.json().get("value", [])
            files = []
            
            for item in items:
                if not item.get("folder"):
                    # Adiciona informação de nível hierárquico ao arquivo
                    nivel = folder_path.count('/') + 1
                    item['_nivel_hierarquico'] = nivel
                    item['_caminho_pasta'] = folder_path
                    
                    # Filtra por extensão, se especificado
                    nome = item.get("name", "").lower()
                    if any(nome.endswith(ext.lower()) for ext in extensoes_validas):
                        # Tenta identificar categoria com base no caminho/nome
                        if "guia_rapido" in folder_path.lower() or "guia rápido" in folder_path.lower():
                            item['_categoria'] = "Guia Rápido"
                        elif "comunicado" in nome.lower():
                            item['_categoria'] = "Comunicado"
                        
                        files.append(item)
            
            return files
        else:
            st.warning(f"Erro ao listar arquivos em {folder_path}: {response.status_code}")
            return []
    except Exception as e:
        st.warning(f"Erro ao listar arquivos em {folder_path}: {str(e)}")
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
        response = requests.get(url, headers=headers, timeout=30)
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
                    # Adiciona nível hierárquico à pasta
                    nivel = nova_pasta.count('/')
                    item['_nivel_hierarquico'] = nivel
                    
                    sub_arquivos = listar_todos_os_arquivos(token, drive_id, nova_pasta, limite=limite)
                    arquivos.extend(sub_arquivos)
                else:
                    # Adiciona nível hierárquico aos arquivos
                    nivel = caminho_pasta.count('/')
                    item['_nivel_hierarquico'] = nivel
                    item['_caminho_pasta'] = caminho_pasta
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

def baixar_arquivo(token, download_url, nome_arquivo, caminho_pasta="/", pasta_destino=DATA_DIR):
    """Baixa um único arquivo e retorna o caminho local"""
    headers = {"Authorization": f"Bearer {token}"}
    # Preserva a informação do caminho da pasta no nome do arquivo
    nome_arquivo_salvo = f"{caminho_pasta.replace('/', '_')}_{nome_arquivo}" if caminho_pasta != "/" else nome_arquivo
    nome_arquivo_salvo = nome_arquivo_salvo.replace(':', '_').replace('?', '_').replace('*', '_')
    
    caminho_local = os.path.join(pasta_destino, nome_arquivo_salvo)
    
    try:
        response = requests.get(download_url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Salva o arquivo localmente
            with open(caminho_local, "wb") as f:
                f.write(response.content)
            return caminho_local, response.content, caminho_pasta
        else:
            st.warning(f"Erro ao baixar {nome_arquivo}: {response.status_code}")
            return None, None, None
    except Exception as e:
        st.warning(f"Erro ao baixar {nome_arquivo}: {str(e)}")
        return None, None, None

def pre_processar_imagem(img):
    """Aplica técnicas de pré-processamento para melhorar a qualidade do OCR"""
    if not use_preprocessing:
        return img
    
    # Converte para RGB se tiver canal alpha
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    # Aplica as técnicas selecionadas
    if "Escala de cinza" in preprocessing_options:
        img = img.convert('L')
    
    if "Aumentar contraste" in preprocessing_options:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
    
    if "Remover ruído" in preprocessing_options:
        img = img.filter(ImageFilter.MedianFilter(size=3))
    
    if "Nitidez" in preprocessing_options:
        img = img.filter(ImageFilter.SHARPEN)
    
    return img

def extrair_texto_de_imagem(img_data_or_path, nivel_hierarquico=0, caminho_pasta="/"):
    """Extrai texto de uma imagem usando OCR"""
    try:
        # Se for um caminho para arquivo
        if isinstance(img_data_or_path, str):
            if not os.path.exists(img_data_or_path):
                return ""
            img = Image.open(img_data_or_path)
            
            # Extrai o nome do arquivo para análise
            nome_arquivo = os.path.basename(img_data_or_path)
        # Se for conteúdo binário
        elif isinstance(img_data_or_path, bytes):
            img = Image.open(io.BytesIO(img_data_or_path))
            nome_arquivo = "arquivo_binario.png"
        # Se já for um objeto PIL Image
        elif isinstance(img_data_or_path, Image.Image):
            img = img_data_or_path
            nome_arquivo = "imagem.png"
        else:
            return ""
        
        # Aplica pré-processamento para melhorar a qualidade do OCR
        img = pre_processar_imagem(img)
            
        # Extrai o texto usando pytesseract
        texto = pytesseract.image_to_string(img, lang=ocr_language)
        texto_limpo = texto.strip() if texto else "[imagem sem texto legível]"
        
        # Adiciona informações de contexto hierárquico
        if nivel_hierarquico > 0 or caminho_pasta != "/":
            prefixo = f"[Nível {nivel_hierarquico}]"
            if caminho_pasta != "/":
                prefixo += f" [Caminho: {caminho_pasta}]"
                
            # Identifica menus e botões baseados no nome do arquivo e conteúdo
            if "guia" in nome_arquivo.lower() and "pratico" in nome_arquivo.lower():
                prefixo += " [Menu: Guia Prático]"
            elif "comunicado" in texto_limpo.lower():
                prefixo += " [Tipo: Comunicado]"
                
            texto_limpo = f"{prefixo}\n{texto_limpo}"
        
        return texto_limpo
    except Exception as e:
        st.error(f"Erro ao processar imagem com OCR: {str(e)}")
        return f"[erro ao processar imagem: {str(e)}]"

def extrair_texto_de_pdf_com_pymupdf(pdf_data_or_path, nivel_hierarquico=0, caminho_pasta="/"):
    """Extrai texto de um PDF usando PyMuPDF (alternativa ao Poppler)"""
    try:
        import fitz  # PyMuPDF
        
        # Se for um caminho para arquivo
        if isinstance(pdf_data_or_path, str):
            if not os.path.exists(pdf_data_or_path):
                return ""
            # Extrai o nome do arquivo para análise
            nome_arquivo = os.path.basename(pdf_data_or_path)
            doc = fitz.open(pdf_data_or_path)
        # Se for conteúdo binário
        elif isinstance(pdf_data_or_path, bytes):
            nome_arquivo = "arquivo_binario.pdf"
            doc = fitz.open(stream=pdf_data_or_path, filetype="pdf")
        else:
            return ""
        
        # Extrai texto de cada página
        textos = []
        for i in range(len(doc)):
            page = doc[i]
            
            # Tenta extrair texto diretamente
            texto = page.get_text()
            
            # Se a página tiver texto
            if texto.strip():
                textos.append(f"--- Página {i+1} ---\n{texto}")
            else:
                # Se não houver texto, extrai como imagem e aplica OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                
                # Converte para PIL Image
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                
                # Aplica OCR na imagem
                texto_ocr = extrair_texto_de_imagem(img)
                if texto_ocr and texto_ocr != "[imagem sem texto legível]":
                    textos.append(f"--- Página {i+1} (OCR) ---\n{texto_ocr}")
        
        # Combina o texto de todas as páginas
        texto_combinado = "\n\n".join(textos) if textos else "[PDF sem texto legível]"
        
        # Adiciona informações de contexto hierárquico
        if nivel_hierarquico > 0 or caminho_pasta != "/":
            prefixo = f"[Nível {nivel_hierarquico}]"
            if caminho_pasta != "/":
                prefixo += f" [Caminho: {caminho_pasta}]"
                
            # Identifica tipos de documento baseados no nome
            if "guia" in nome_arquivo.lower():
                prefixo += " [Tipo: Guia]"
            elif "comunicado" in nome_arquivo.lower():
                prefixo += " [Tipo: Comunicado]"
                
            texto_combinado = f"{prefixo}\n{texto_combinado}"
        
        return texto_combinado
    except Exception as e:
        st.error(f"Erro ao processar PDF com PyMuPDF: {str(e)}")
        return f"[erro ao processar PDF com PyMuPDF: {str(e)}]"

# NOVA FUNÇÃO: Mapear estrutura completa do SharePoint
def mapear_estrutura_sharepoint(token: str, site_id: str = SITE_ID, detalhado: bool = True) -> Dict[str, Any]:
    """
    Mapeia a estrutura completa do SharePoint para identificar os caminhos corretos.
    
    Args:
        token: Token de autenticação para a Microsoft Graph API
        site_id: ID do site SharePoint
        detalhado: Se True, inclui informações detalhadas sobre cada item
        
    Returns:
        Dicionário com a estrutura completa do SharePoint
    """
    st.info("Iniciando mapeamento da estrutura do SharePoint...")
    
    # Estrutura para armazenar o mapeamento completo
    estrutura_completa = {
        "bibliotecas": {},
        "listas": {},
        "paginas": {},
        "navegacao": {},
        "metadata": {
            "site_id": site_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_bibliotecas": 0,
            "total_pastas": 0,
            "total_arquivos": 0
        }
    }
    
    # 1. Lista todas as bibliotecas
    try:
        bibliotecas = listar_bibliotecas(token)
        estrutura_completa["metadata"]["total_bibliotecas"] = len(bibliotecas)
        
        for biblioteca in bibliotecas:
            biblioteca_id = biblioteca.get("id")
            biblioteca_nome = biblioteca.get("name")
            biblioteca_url = biblioteca.get("webUrl", "")
            
            st.info(f"Mapeando biblioteca: {biblioteca_nome}")
            
            # Estrutura para esta biblioteca
            estrutura_biblioteca = {
                "id": biblioteca_id,
                "nome": biblioteca_nome,
                "url": biblioteca_url,
                "pastas_raiz": [],
                "arquivos_raiz": [],
                "total_pastas": 0,
                "total_arquivos": 0
            }
            
            # 2. Lista pastas e arquivos na raiz da biblioteca
            try:
                # Lista pastas na raiz
                pastas_raiz = listar_pastas(token, biblioteca_id)
                estrutura_biblioteca["total_pastas"] += len(pastas_raiz)
                estrutura_completa["metadata"]["total_pastas"] += len(pastas_raiz)
                
                # Lista arquivos na raiz
                arquivos_raiz = listar_arquivos(token, biblioteca_id)
                estrutura_biblioteca["total_arquivos"] += len(arquivos_raiz)
                estrutura_completa["metadata"]["total_arquivos"] += len(arquivos_raiz)
                
                # Adiciona informações básicas sobre pastas
                for pasta in pastas_raiz:
                    pasta_info = {
                        "nome": pasta.get("name"),
                        "id": pasta.get("id"),
                        "caminho": "/",
                        "url": pasta.get("webUrl", "")
                    }
                    
                    # Se detalhado, explora recursivamente a estrutura de subpastas
                    if detalhado:
                        pasta_info["conteudo"] = _mapear_pasta_recursivamente(
                            token, 
                            biblioteca_id, 
                            f"/{pasta.get('name')}", 
                            estrutura_completa["metadata"]
                        )
                    
                    estrutura_biblioteca["pastas_raiz"].append(pasta_info)
                
                # Adiciona informações básicas sobre arquivos
                for arquivo in arquivos_raiz:
                    arquivo_info = {
                        "nome": arquivo.get("name"),
                        "id": arquivo.get("id"),
                        "tipo": arquivo.get("file", {}).get("mimeType", ""),
                        "tamanho": arquivo.get("size", 0),
                        "url": arquivo.get("webUrl", ""),
                        "download_url": arquivo.get("@microsoft.graph.downloadUrl", "")
                    }
                    estrutura_biblioteca["arquivos_raiz"].append(arquivo_info)
                
                # Adiciona esta biblioteca à estrutura completa
                estrutura_completa["bibliotecas"][biblioteca_nome] = estrutura_biblioteca
                
            except Exception as e:
                st.warning(f"Erro ao mapear conteúdo da biblioteca {biblioteca_nome}: {str(e)}")
                estrutura_biblioteca["erro"] = str(e)
                estrutura_completa["bibliotecas"][biblioteca_nome] = estrutura_biblioteca
        
        # 3. Tenta obter informações de navegação do site
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Obtém informações de navegação
            nav_url = f"{GRAPH_ROOT}/sites/{site_id}/navigation"
            response = requests.get(nav_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                estrutura_completa["navegacao"] = response.json()
            else:
                estrutura_completa["navegacao"]["erro"] = f"Erro {response.status_code}"
            
            # Obtém páginas do site
            pages_url = f"{GRAPH_ROOT}/sites/{site_id}/pages"
            response = requests.get(pages_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                paginas = response.json().get("value", [])
                estrutura_completa["paginas"] = {
                    "total": len(paginas),
                    "items": []
                }
                
                for pagina in paginas:
                    estrutura_completa["paginas"]["items"].append({
                        "nome": pagina.get("name", ""),
                        "titulo": pagina.get("title", ""),
                        "url": pagina.get("webUrl", "")
                    })
            else:
                estrutura_completa["paginas"]["erro"] = f"Erro {response.status_code}"
                
            # Obtém listas do site
            lists_url = f"{GRAPH_ROOT}/sites/{site_id}/lists"
            response = requests.get(lists_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                listas = response.json().get("value", [])
                estrutura_completa["listas"] = {
                    "total": len(listas),
                    "items": []
                }
                
                for lista in listas:
                    estrutura_completa["listas"]["items"].append({
                        "nome": lista.get("name", ""),
                        "displayName": lista.get("displayName", ""),
                        "url": lista.get("webUrl", "")
                    })
            else:
                estrutura_completa["listas"]["erro"] = f"Erro {response.status_code}"
                
        except Exception as e:
            st.warning(f"Erro ao obter informações de navegação: {str(e)}")
            estrutura_completa["navegacao"]["erro"] = str(e)
    
    except Exception as e:
        st.error(f"Erro ao mapear estrutura do SharePoint: {str(e)}")
        estrutura_completa["erro"] = str(e)
    
    st.success(f"Mapeamento concluído! Encontradas {estrutura_completa['metadata']['total_bibliotecas']} bibliotecas, {estrutura_completa['metadata']['total_pastas']} pastas e {estrutura_completa['metadata']['total_arquivos']} arquivos.")
    
    return estrutura_completa

def _mapear_pasta_recursivamente(token: str, drive_id: str, caminho_pasta: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função auxiliar para mapear recursivamente o conteúdo de uma pasta.
    
    Args:
        token: Token de autenticação
        drive_id: ID da biblioteca
        caminho_pasta: Caminho da pasta
        metadata: Dicionário de metadados para atualizar contadores
        
    Returns:
        Dicionário com a estrutura da pasta
    """
    resultado = {
        "pastas": [],
        "arquivos": [],
        "total_pastas": 0,
        "total_arquivos": 0
    }
    
    # Lista pastas neste caminho
    pastas = listar_pastas(token, drive_id, caminho_pasta)
    resultado["total_pastas"] = len(pastas)
    metadata["total_pastas"] += len(pastas)
    
    # Lista arquivos neste caminho
    arquivos = listar_arquivos(token, drive_id, caminho_pasta)
    resultado["total_arquivos"] = len(arquivos)
    metadata["total_arquivos"] += len(arquivos)
    
    # Processa pastas
    for pasta in pastas:
        pasta_nome = pasta.get("name")
        novo_caminho = f"{caminho_pasta}/{pasta_nome}".replace("//", "/")
        
        pasta_info = {
            "nome": pasta_nome,
            "id": pasta.get("id"),
            "caminho": caminho_pasta,
            "url": pasta.get("webUrl", "")
        }
        
        # Mapeia recursivamente o conteúdo desta pasta
        pasta_info["conteudo"] = _mapear_pasta_recursivamente(
            token, drive_id, novo_caminho, metadata
        )
        
        resultado["pastas"].append(pasta_info)
    
    # Processa arquivos
    for arquivo in arquivos:
        arquivo_info = {
            "nome": arquivo.get("name"),
            "id": arquivo.get("id"),
            "tipo": arquivo.get("file", {}).get("mimeType", ""),
            "tamanho": arquivo.get("size", 0),
            "url": arquivo.get("webUrl", ""),
            "download_url": arquivo.get("@microsoft.graph.downloadUrl", "")
        }
        resultado["arquivos"].append(arquivo_info)
    
    return resultado

def _exibir_pasta_recursivamente(pasta, nivel):
    """
    Função auxiliar para exibir recursivamente a estrutura de pastas no Streamlit.
    
    Args:
        pasta: Dicionário com informações da pasta
        nivel: Nível de indentação
    """
    indentacao = "  " * nivel
    st.write(f"{indentacao}- 📁 {pasta['nome']}")
    
    if "conteudo" in pasta:
        conteudo = pasta["conteudo"]
        
        # Exibe arquivos
        for arquivo in conteudo.get("arquivos", []):
            st.write(f"{indentacao}  - 📄 {arquivo['nome']}")
        
        # Exibe subpastas recursivamente
        for subpasta in conteudo.get("pastas", []):
            _exibir_pasta_recursivamente(subpasta, nivel + 1)

# NOVA FUNÇÃO: Explorar estrutura do SharePoint via interface Streamlit
def explorar_estrutura_sharepoint():
    """
    Função para explorar e visualizar a estrutura completa do SharePoint.
    """
    st.header("🔍 Explorador de Estrutura do SharePoint")
    
    st.markdown("""
    Esta ferramenta mapeia a estrutura completa do SharePoint, incluindo bibliotecas, 
    pastas, arquivos, listas e elementos de navegação. Isso ajuda a identificar 
    problemas de acesso e entender a organização real dos documentos.
    """)
    
    # Obtém token de autenticação
    token = get_graph_token()
    if not token:
        st.error("❌ Não foi possível obter token de autenticação. Verifique as credenciais.")
        return
    
    # Opções de mapeamento
    col1, col2 = st.columns(2)
    with col1:
        mapeamento_detalhado = st.checkbox("Mapeamento detalhado", value=True, 
                                          help="Inclui informações detalhadas sobre cada item")
    with col2:
        salvar_resultado = st.checkbox("Salvar resultado em arquivo", value=True,
                                      help="Salva o resultado do mapeamento em um arquivo JSON")
    
    # Botão para iniciar o mapeamento
    if st.button("🔄 Iniciar Mapeamento Completo"):
        with st.spinner("Mapeando estrutura do SharePoint..."):
            # Executa o mapeamento
            estrutura = mapear_estrutura_sharepoint(token, SITE_ID, mapeamento_detalhado)
            
            # Exibe resumo
            st.success(f"✅ Mapeamento concluído!")
            
            # Cria abas para diferentes visualizações
            tab1, tab2, tab3, tab4 = st.tabs(["Resumo", "Bibliotecas", "Navegação", "JSON Completo"])
            
            with tab1:
                st.subheader("Resumo do Mapeamento")
                
                # Métricas principais
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Bibliotecas", estrutura["metadata"]["total_bibliotecas"])
                with col2:
                    st.metric("Pastas", estrutura["metadata"]["total_pastas"])
                with col3:
                    st.metric("Arquivos", estrutura["metadata"]["total_arquivos"])
                
                # Informações sobre listas e páginas
                if "listas" in estrutura and "total" in estrutura["listas"]:
                    st.metric("Listas", estrutura["listas"]["total"])
                if "paginas" in estrutura and "total" in estrutura["paginas"]:
                    st.metric("Páginas", estrutura["paginas"]["total"])
            
            with tab2:
                st.subheader("Estrutura de Bibliotecas")
                
                # Lista as bibliotecas encontradas
                for nome_biblioteca, dados in estrutura["bibliotecas"].items():
                    with st.expander(f"📁 {nome_biblioteca} ({dados['total_arquivos']} arquivos, {dados['total_pastas']} pastas)"):
                        st.write(f"**URL:** {dados['url']}")
                        st.write(f"**ID:** {dados['id']}")
                        
                        # Mostra arquivos na raiz
                        if dados["arquivos_raiz"]:
                            st.write("**Arquivos na raiz:**")
                            for arquivo in dados["arquivos_raiz"]:
                                st.write(f"- 📄 {arquivo['nome']} ({arquivo['tipo']})")
                        
                        # Mostra pastas na raiz
                        if dados["pastas_raiz"]:
                            st.write("**Pastas na raiz:**")
                            for pasta in dados["pastas_raiz"]:
                                _exibir_pasta_recursivamente(pasta, 1)
            
            with tab3:
                st.subheader("Elementos de Navegação")
                
                # Exibe informações de navegação
                if "navegacao" in estrutura and not "erro" in estrutura["navegacao"]:
                    if "quickLaunch" in estrutura["navegacao"]:
                        st.write("**Menu de Navegação Rápida:**")
                        for item in estrutura["navegacao"]["quickLaunch"].get("value", []):
                            st.write(f"- 🔗 {item.get('displayName')}: {item.get('url')}")
                    
                    if "topNavigationBar" in estrutura["navegacao"]:
                        st.write("**Barra de Navegação Superior:**")
                        for item in estrutura["navegacao"]["topNavigationBar"].get("value", []):
                            st.write(f"- 🔗 {item.get('displayName')}: {item.get('url')}")
                else:
                    st.warning("Não foi possível obter informações de navegação.")
            
            with tab4:
                st.subheader("Dados JSON Completos")
                st.json(estrutura)
            
            # Salva o resultado em arquivo
            if salvar_resultado:
                # Cria pasta para resultados se não existir
                resultado_dir = "resultados_mapeamento"
                if not os.path.exists(resultado_dir):
                    os.makedirs(resultado_dir)
                
                # Nome do arquivo com timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                arquivo_json = os.path.join(resultado_dir, f"mapeamento_sharepoint_{timestamp}.json")
                
                # Salva o arquivo
                with open(arquivo_json, "w", encoding="utf-8") as f:
                    json.dump(estrutura, f, ensure_ascii=False, indent=2)
                
                st.success(f"✅ Resultado salvo em: {arquivo_json}")
                
                # Oferece download do arquivo
                with open(arquivo_json, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="📥 Baixar Resultado do Mapeamento",
                        data=f,
                        file_name=f"mapeamento_sharepoint_{timestamp}.json",
                        mime="application/json"
                    )

# NOVA FUNÇÃO: Acessar documentos via Selenium
def inicializar_selenium():
    """
    Inicializa o navegador Selenium para navegação avançada.
    
    Returns:
        Instância do navegador Selenium ou None em caso de erro
    """
    if not selenium_disponivel:
        st.error("❌ Selenium não está instalado. Instale com: pip install selenium webdriver-manager")
        return None
    
    try:
        # Configura as opções do Chrome
        options = Options()
        options.add_argument("--headless")  # Executa em modo headless (sem interface gráfica)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Inicializa o driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        return driver
    except Exception as e:
        st.error(f"❌ Erro ao inicializar Selenium: {str(e)}")
        return None

def autenticar_sharepoint_selenium(driver, token):
    """
    Autentica no SharePoint usando o token obtido.
    
    Args:
        driver: Instância do navegador Selenium
        token: Token de autenticação
        
    Returns:
        True se autenticado com sucesso, False caso contrário
    """
    try:
        # Armazena o token em um cookie ou localStorage
        # Nota: Esta é uma simplificação, a autenticação real pode ser mais complexa
        driver.get(SHAREPOINT_URL)
        
        # Injeta o token via JavaScript
        script = f"""
        localStorage.setItem('graphToken', '{token}');
        """
        driver.execute_script(script)
        
        # Verifica se a página carregou corretamente
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        return True
    except Exception as e:
        st.error(f"❌ Erro ao autenticar no SharePoint: {str(e)}")
        return False

def navegar_para_secao(driver, secao):
    """
    Navega para uma seção específica do Guia Rápido.
    
    Args:
        driver: Instância do navegador Selenium
        secao: Nome da seção (Operações, Monitoria, Treinamento)
        
    Returns:
        True se navegou com sucesso, False caso contrário
    """
    try:
        # Espera a página carregar completamente
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Tenta encontrar o elemento da seção pelo texto
        xpath_secao = f"//span[contains(text(), '{secao}')]"
        
        # Espera o elemento ficar visível e clicável
        elemento_secao = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath_secao))
        )
        
        # Rola até o elemento para garantir que está visível
        driver.execute_script("arguments[0].scrollIntoView(true);", elemento_secao)
        
        # Clica no elemento
        elemento_secao.click()
        
        # Espera a seção carregar
        time.sleep(2)
        
        return True
    except Exception as e:
        st.warning(f"⚠️ Erro ao navegar para a seção {secao}: {str(e)}")
        return False

def extrair_documentos_da_secao(driver, secao):
    """
    Extrai informações sobre documentos de uma seção específica.
    
    Args:
        driver: Instância do navegador Selenium
        secao: Nome da seção atual
        
    Returns:
        Lista de dicionários com informações dos documentos
    """
    documentos = []
    
    try:
        # Espera os documentos carregarem
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Captura uma screenshot para debug
        screenshot_path = f"secao_{secao.lower().replace(' ', '_')}.png"
        driver.save_screenshot(screenshot_path)
        
        # Tenta diferentes seletores para encontrar os documentos
        seletores = [
            "div.ms-DocumentCard",  # Cartões de documento padrão do SharePoint
            "div.ms-List-cell",     # Células de lista
            "div.ms-DetailsRow",    # Linhas de detalhes
            "a[href*='.pdf']",      # Links para PDFs
            "a[href*='.jpg'], a[href*='.png'], a[href*='.jpeg']"  # Links para imagens
        ]
        
        for seletor in seletores:
            try:
                # Tenta encontrar elementos com este seletor
                elementos = driver.find_elements(By.CSS_SELECTOR, seletor)
                
                if elementos:
                    st.info(f"Encontrados {len(elementos)} elementos com o seletor '{seletor}' na seção {secao}")
                    
                    for elemento in elementos:
                        try:
                            # Tenta extrair informações do documento
                            doc_info = {"secao": secao}
                            
                            # Tenta encontrar o título
                            try:
                                titulo_elem = elemento.find_element(By.CSS_SELECTOR, "span.ms-DocumentCard-title, span.ms-Link")
                                doc_info["nome"] = titulo_elem.text.strip()
                            except:
                                # Se não encontrar um título específico, usa o texto do elemento
                                doc_info["nome"] = elemento.text.strip() or "Documento sem título"
                            
                            # Tenta encontrar o link
                            try:
                                link_elem = elemento.find_element(By.TAG_NAME, "a")
                                doc_info["url"] = link_elem.get_attribute("href")
                            except:
                                # Se o próprio elemento for um link
                                if elemento.tag_name == "a":
                                    doc_info["url"] = elemento.get_attribute("href")
                                else:
                                    doc_info["url"] = ""
                            
                            # Adiciona à lista se tiver informações mínimas
                            if doc_info.get("nome") and doc_info.get("url"):
                                documentos.append(doc_info)
                        except Exception as e:
                            st.warning(f"Erro ao processar elemento: {str(e)}")
                            continue
                    
                    # Se encontrou documentos com este seletor, interrompe a busca
                    if documentos:
                        break
            except Exception as e:
                continue
        
        # Se não encontrou documentos com os seletores específicos, tenta uma abordagem mais genérica
        if not documentos:
            st.warning(f"Não foi possível encontrar documentos com seletores específicos na seção {secao}. Tentando abordagem genérica...")
            
            # Captura todos os links da página
            links = driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    texto = link.text.strip()
                    
                    # Filtra apenas links que parecem ser documentos
                    if href and texto and (
                        ".pdf" in href.lower() or 
                        ".jpg" in href.lower() or 
                        ".png" in href.lower() or 
                        ".jpeg" in href.lower() or
                        "documentos" in href.lower()
                    ):
                        documentos.append({
                            "nome": texto or "Link para documento",
                            "url": href,
                            "secao": secao,
                            "tipo": "link_generico"
                        })
                except:
                    continue
    
    except Exception as e:
        st.error(f"❌ Erro ao extrair documentos da seção {secao}: {str(e)}")
    
    return documentos

def acessar_documentos_via_selenium():
    """
    Acessa documentos do SharePoint usando navegação avançada com Selenium.
    """
    st.header("🌐 Navegação Avançada do SharePoint")
    
    st.markdown("""
    Esta ferramenta usa automação de navegador para acessar documentos que não estão 
    disponíveis diretamente via API. Navega pelas diferentes seções do Guia Rápido 
    (Operações, Monitoria, Treinamento) e extrai informações sobre os documentos.
    """)
    
    # Verifica se o Selenium está disponível
    if not selenium_disponivel:
        st.error("❌ Selenium não está instalado. Instale com: pip install selenium webdriver-manager")
        return
    
    # Obtém token de autenticação
    token = get_graph_token()
    if not token:
        st.error("❌ Não foi possível obter token de autenticação. Verifique as credenciais.")
        return
    
    # Opções de navegação
    secoes = ["Operações", "Monitoria", "Treinamento"]
    secoes_selecionadas = st.multiselect(
        "Selecione as seções para navegar:",
        options=secoes,
        default=secoes,
        help="Escolha quais seções do Guia Rápido deseja explorar"
    )
    
    # Botão para iniciar a navegação
    if st.button("🚀 Iniciar Navegação Avançada"):
        if not secoes_selecionadas:
            st.warning("⚠️ Selecione pelo menos uma seção para navegar.")
            return
        
        with st.spinner("Inicializando navegador..."):
            # Inicializa o Selenium
            driver = inicializar_selenium()
            
            if not driver:
                st.error("❌ Não foi possível inicializar o navegador Selenium.")
                return
            
            try:
                # Navega para o SharePoint
                st.info(f"Navegando para {SHAREPOINT_URL}...")
                driver.get(SHAREPOINT_URL)
                
                # Espera a página carregar
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Captura screenshot inicial
                driver.save_screenshot("pagina_inicial.png")
                st.image("pagina_inicial.png", caption="Página inicial do SharePoint", width=600)
                
                # Dicionário para armazenar os documentos encontrados
                todos_documentos = {}
                total_documentos = 0
                
                # Navega por cada seção selecionada
                for secao in secoes_selecionadas:
                    st.subheader(f"Navegando para seção: {secao}")
                    
                    # Tenta navegar para a seção
                    if navegar_para_secao(driver, secao):
                        # Captura screenshot da seção
                        screenshot_path = f"secao_{secao.lower().replace(' ', '_')}.png"
                        driver.save_screenshot(screenshot_path)
                        st.image(screenshot_path, caption=f"Seção: {secao}", width=600)
                        
                        # Extrai documentos da seção
                        documentos = extrair_documentos_da_secao(driver, secao)
                        
                        # Armazena os documentos encontrados
                        todos_documentos[secao] = documentos
                        total_documentos += len(documentos)
                        
                        st.success(f"✅ Encontrados {len(documentos)} documentos na seção {secao}")
                    else:
                        st.warning(f"⚠️ Não foi possível navegar para a seção {secao}")
                
                # Exibe resumo dos documentos encontrados
                st.subheader("Resumo dos Documentos Encontrados")
                st.metric("Total de Documentos", total_documentos)
                
                # Exibe os documentos por seção
                for secao, documentos in todos_documentos.items():
                    with st.expander(f"{secao} ({len(documentos)} documentos)"):
                        if documentos:
                            for i, doc in enumerate(documentos):
                                st.write(f"{i+1}. **{doc.get('nome', 'Documento sem título')}**")
                                st.write(f"   URL: {doc.get('url', 'Sem URL')}")
                                st.write("---")
                        else:
                            st.write("Nenhum documento encontrado nesta seção.")
                
                # Salva os resultados em um arquivo JSON
                resultado_dir = "resultados_navegacao"
                if not os.path.exists(resultado_dir):
                    os.makedirs(resultado_dir)
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                arquivo_json = os.path.join(resultado_dir, f"documentos_sharepoint_{timestamp}.json")
                
                with open(arquivo_json, "w", encoding="utf-8") as f:
                    json.dump(todos_documentos, f, ensure_ascii=False, indent=2)
                
                st.success(f"✅ Resultados salvos em: {arquivo_json}")
                
                # Oferece download do arquivo
                with open(arquivo_json, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="📥 Baixar Resultados da Navegação",
                        data=f,
                        file_name=f"documentos_sharepoint_{timestamp}.json",
                        mime="application/json"
                    )
                
            except Exception as e:
                st.error(f"❌ Erro durante a navegação: {str(e)}")
                st.code(traceback.format_exc())
            
            finally:
                # Fecha o navegador
                driver.quit()
                st.info("Navegador fechado.")

# Interface principal do aplicativo
def main():
    # Cria abas para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["Consulta de Documentos", "Explorador de Estrutura", "Navegação Avançada"])
    
    with tab1:
        # Obtém token de autenticação
        token = get_graph_token()
        if not token:
            st.error("❌ Não foi possível obter token de autenticação. Verifique as credenciais.")
            return
        
        # Lista bibliotecas disponíveis
        bibliotecas = listar_bibliotecas(token)
        if not bibliotecas:
            st.error("❌ Não foi possível listar as bibliotecas do SharePoint.")
            return
        
        # Seleção de biblioteca
        biblioteca_selecionada = st.selectbox(
            "Selecione uma biblioteca:",
            options=[b["name"] for b in bibliotecas],
            format_func=lambda x: f"{x} ({next((b['driveType'] for b in bibliotecas if b['name'] == x), '')})"
        )
        
        # Obtém o ID da biblioteca selecionada
        drive_id = next((b["id"] for b in bibliotecas if b["name"] == biblioteca_selecionada), None)
        
        if drive_id:
            # Botão para listar arquivos
            if st.button("🔍 Buscar Documentos"):
                # Barra de progresso
                progress_bar = st.progress(0, text="Iniciando busca...")
                
                # Lista todos os arquivos na biblioteca
                arquivos = listar_todos_os_arquivos(token, drive_id, progress_bar=progress_bar)
                
                # Exibe resultados
                st.subheader("Documentos Encontrados")
                st.write(f"Total de documentos: {len(arquivos)}")
                
                # Agrupa por seção
                arquivos_por_secao = {}
                for arquivo in arquivos:
                    caminho = arquivo.get("_caminho_pasta", "/")
                    secao = "Raiz"
                    
                    # Tenta identificar a seção com base no caminho
                    if "operacoes" in caminho.lower() or "operações" in caminho.lower():
                        secao = "Operações"
                    elif "monitoria" in caminho.lower():
                        secao = "Monitoria"
                    elif "treinamento" in caminho.lower():
                        secao = "Treinamento"
                    elif "documentos" in caminho.lower():
                        secao = "Documentos"
                    
                    # Adiciona à seção correspondente
                    if secao not in arquivos_por_secao:
                        arquivos_por_secao[secao] = []
                    arquivos_por_secao[secao].append(arquivo)
                
                # Exibe arquivos por seção
                for secao, arquivos_secao in arquivos_por_secao.items():
                    with st.expander(f"Seção {secao}: {len(arquivos_secao)} documentos"):
                        for arquivo in arquivos_secao:
                            st.write(f"📄 {arquivo.get('name')} ({arquivo.get('_caminho_pasta', '/')})")
    
    with tab2:
        # Explorador de estrutura do SharePoint
        explorar_estrutura_sharepoint()
    
    with tab3:
        # Navegação avançada com Selenium
        acessar_documentos_via_selenium()

if __name__ == "__main__":
    main()
