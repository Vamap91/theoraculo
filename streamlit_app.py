"""
ORÁCULO - Análise Inteligente de Documentos do SharePoint
Aplicação principal adaptada para estrutura hierárquica do Guia Rápido da Carglass.
"""

import os
import tempfile
import platform
import streamlit as st
import requests
import io
import traceback
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import time
from openai import OpenAI
import numpy as np

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

# Verifica e cria o diretório para armazenar os arquivos, se não existir
if not os.path.exists(DATA_DIR):
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
        return f"[erro ao processar PDF: {str(e)}]"

def extrair_texto_de_pdf_com_pdf2image(pdf_data_or_path, nivel_hierarquico=0, caminho_pasta="/"):
    """Extrai texto de um PDF usando pdf2image e OCR"""
    try:
        # Se for um caminho para arquivo
        if isinstance(pdf_data_or_path, str):
            if not os.path.exists(pdf_data_or_path):
                return ""
            nome_arquivo = os.path.basename(pdf_data_or_path)
            with open(pdf_data_or_path, 'rb') as f:
                pdf_data = f.read()
        # Se for conteúdo binário
        elif isinstance(pdf_data_or_path, bytes):
            pdf_data = pdf_data_or_path
            nome_arquivo = "arquivo_binario.pdf"
        else:
            return ""
        
        # Cria um arquivo temporário para o PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf.write(pdf_data)
            temp_pdf_path = temp_pdf.name
        
        try:
            # Converte PDF para imagens
            imagens = pdf2image.convert_from_path(temp_pdf_path, dpi=300)
        except Exception as e:
            os.unlink(temp_pdf_path)
            # Se falhar com Poppler, tenta processar diretamente como imagem
            if "Unable to get page count" in str(e):
                st.info("Tentando processar o PDF como imagem devido a problemas com o Poppler.")
                try:
                    return extrair_texto_de_imagem(pdf_data, nivel_hierarquico, caminho_pasta)
                except:
                    pass
            return f"[erro ao processar PDF: {str(e)}]"
        
        # Remove o arquivo temporário
        os.unlink(temp_pdf_path)
        
        # Extrai texto de cada página
        textos = []
        for i, img in enumerate(imagens):
            texto_pagina = extrair_texto_de_imagem(img)
            if texto_pagina and texto_pagina != "[imagem sem texto legível]":
                textos.append(f"--- Página {i+1} ---\n{texto_pagina}")
        
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
        st.error(f"Erro ao processar PDF com pdf2image: {str(e)}")
        return f"[erro ao processar PDF: {str(e)}]"

def detectar_tipo_arquivo(conteudo_binario):
    """Detecta o tipo MIME de um arquivo usando python-magic, se disponível"""
    if has_magic and isinstance(conteudo_binario, bytes):
        try:
            return magic.from_buffer(conteudo_binario, mime=True)
        except:
            pass
    return None

def extrair_texto_de_arquivo(caminho_ou_conteudo, nome_arquivo=None, nivel_hierarquico=0, caminho_pasta="/"):
    """Extrai texto de um arquivo com detecção inteligente de formato"""
    # Determina a extensão e o nome do arquivo
    if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
        nome = os.path.basename(caminho_ou_conteudo).lower()
    else:
        nome = nome_arquivo.lower() if nome_arquivo else ""
    
    # Detecta o tipo real do arquivo, se possível
    mime_type = None
    if isinstance(caminho_ou_conteudo, bytes):
        mime_type = detectar_tipo_arquivo(caminho_ou_conteudo)
    
    # Define a estratégia com base no tipo MIME ou extensão
    if mime_type:
        if 'image' in mime_type:
            return extrair_texto_de_imagem(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
        elif 'pdf' in mime_type:
            if pdf_processor == "pymupdf":
                return extrair_texto_de_pdf_com_pymupdf(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
            else:
                return extrair_texto_de_pdf_com_pdf2image(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
        elif 'text' in mime_type:
            # Extrai texto de arquivos de texto
            try:
                if isinstance(caminho_ou_conteudo, bytes):
                    texto = caminho_ou_conteudo.decode('utf-8', errors='ignore')
                else:
                    with open(caminho_ou_conteudo, 'r', encoding='utf-8', errors='ignore') as f:
                        texto = f.read()
                
                # Adiciona informações de contexto hierárquico
                if nivel_hierarquico > 0 or caminho_pasta != "/":
                    prefixo = f"[Nível {nivel_hierarquico}]"
                    if caminho_pasta != "/":
                        prefixo += f" [Caminho: {caminho_pasta}]"
                    texto = f"{prefixo}\n{texto}"
                
                return texto
            except Exception as e:
                return f"[erro ao ler arquivo de texto: {str(e)}]"
    else:
        # Determina o tipo baseado na extensão do arquivo
        if nome.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return extrair_texto_de_imagem(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
        elif nome.endswith('.pdf'):
            # Tenta primeiro com o processador de PDF configurado
            try:
                if pdf_processor == "pymupdf":
                    return extrair_texto_de_pdf_com_pymupdf(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
                else:
                    return extrair_texto_de_pdf_com_pdf2image(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
            except Exception as e:
                # Se falhar, tenta processar como imagem
                st.warning(f"Erro ao processar PDF, tentando como imagem: {str(e)}")
                return extrair_texto_de_imagem(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
        elif nome.endswith(('.txt', '.csv', '.md')):
            # Extrai texto de arquivos de texto
            try:
                if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
                    with open(caminho_ou_conteudo, 'r', encoding='utf-8', errors='ignore') as f:
                        texto = f.read()
                elif isinstance(caminho_ou_conteudo, bytes):
                    texto = caminho_ou_conteudo.decode('utf-8', errors='ignore')
                else:
                    return "[formato de arquivo não suportado]"
                
                # Adiciona informações de contexto hierárquico
                if nivel_hierarquico > 0 or caminho_pasta != "/":
                    prefixo = f"[Nível {nivel_hierarquico}]"
                    if caminho_pasta != "/":
                        prefixo += f" [Caminho: {caminho_pasta}]"
                    texto = f"{prefixo}\n{texto}"
                
                return texto
            except Exception as e:
                return f"[erro ao ler arquivo de texto: {str(e)}]"
        else:
            # Para extensões desconhecidas, tenta primeiro como imagem
            try:
                return extrair_texto_de_imagem(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
            except:
                # Se falhar, tenta como PDF
                try:
                    if pdf_processor == "pymupdf":
                        return extrair_texto_de_pdf_com_pymupdf(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
                    else:
                        return extrair_texto_de_pdf_com_pdf2image(caminho_ou_conteudo, nivel_hierarquico, caminho_pasta)
                except:
                    pass
    
    # Se todas as tentativas falharem
    return f"[não foi possível extrair texto do formato: {nome}]"

def extrair_info_contexto(texto):
    """Extrai informações de contexto do texto processado"""
    nivel = 0
    caminho = "/"
    tipo = "Desconhecido"
    menu = ""
    
    # Extrai informações das tags de contexto
    if "[Nível " in texto:
        try:
            nivel_str = texto.split("[Nível ")[1].split("]")[0]
            nivel = int(nivel_str)
        except:
            pass
    
    if "[Caminho: " in texto:
        try:
            caminho = texto.split("[Caminho: ")[1].split("]")[0]
        except:
            pass
    
    if "[Tipo: " in texto:
        try:
            tipo = texto.split("[Tipo: ")[1].split("]")[0]
        except:
            pass
    
    if "[Menu: " in texto:
        try:
            menu = texto.split("[Menu: ")[1].split("]")[0]
        except:
            pass
    
    return {
        "nivel": nivel,
        "caminho": caminho,
        "tipo": tipo,
        "menu": menu
    }

def processar_pergunta(pergunta, conteudo_extraido, modelo_ia="gpt-3.5-turbo"):
    """Processa uma pergunta considerando a estrutura hierárquica dos dados"""
    try:
        # Organiza o conteúdo por níveis hierárquicos
        conteudo_por_nivel = {}
        info_contextual = []
        
        for i, texto in enumerate(conteudo_extraido):
            # Extrai informações de contexto
            info = extrair_info_contexto(texto)
            info["indice"] = i
            info["texto"] = texto
            info_contextual.append(info)
            
            # Agrupa por nível hierárquico
            nivel = info["nivel"]
            if nivel not in conteudo_por_nivel:
                conteudo_por_nivel[nivel] = []
            conteudo_por_nivel[nivel].append(texto)
        
        # Ordena os níveis hierárquicos
        niveis_ordenados = sorted(conteudo_por_nivel.keys())
        
        # Monta o contexto hierárquico ordenado
        contexto_ordenado = []
        for nivel in niveis_ordenados:
            contexto_ordenado.extend(conteudo_por_nivel[nivel])
        
        # Se não tiver estrutura hierárquica, usa o conteúdo original
        if not contexto_ordenado:
            contexto_ordenado = conteudo_extraido
        
        # Junta o conteúdo com separadores claros
        contexto = "\n\n---DOCUMENTO HIERÁRQUICO---\n\n".join(contexto_ordenado)
        
        # Prepara informações adicionais de contexto para melhorar a resposta da IA
        info_adicional = "Informações sobre a estrutura hierárquica dos documentos:\n"
        for nivel in niveis_ordenados:
            num_docs = len(conteudo_por_nivel[nivel])
            info_adicional += f"- Nível {nivel}: {num_docs} documento(s)\n"
        
        # Agrupa também por tipo de documento
        tipos = {}
        for info in info_contextual:
            tipo = info["tipo"]
            if tipo not in tipos:
                tipos[tipo] = 0
            tipos[tipo] += 1
        
        for tipo, contagem in tipos.items():
            if tipo != "Desconhecido":
                info_adicional += f"- Tipo '{tipo}': {contagem} documento(s)\n"
        
        # Identifica possíveis menus e botões
        menus = {}
        for info in info_contextual:
            menu = info["menu"]
            if menu and menu not in menus:
                menus[menu] = 0
            if menu:
                menus[menu] += 1
        
        for menu, contagem in menus.items():
            info_adicional += f"- Menu '{menu}': {contagem} documento(s)\n"
        
        # Monta o prompt para a IA
        prompt = f"""
Você é um assistente inteligente especializado em analisar o conteúdo do SharePoint da Carglass.

INFORMAÇÕES SOBRE A ESTRUTURA HIERÁRQUICA:
Os documentos a seguir têm uma estrutura hierárquica com múltiplos níveis:
- Nível 1: Menu principal com botões e opções como "Guia Rápido"
- Nível 2: Subcategorias com botões como "Seguradoras", "Assistências", etc.
- Nível 3: Conteúdo detalhado com procedimentos, contatos e informações específicas

{info_adicional}

CONTEXTO DOS DOCUMENTOS:
{contexto}

INSTRUÇÕES:
1. Baseie sua resposta EXCLUSIVAMENTE nas informações contidas nos documentos fornecidos.
2. Considere a estrutura hierárquica ao responder, indicando de qual seção/nível a informação veio.
3. Se a informação não estiver presente nos documentos, responda claramente: "Não encontrei essa informação nos documentos fornecidos."
4. Se os documentos contiverem informações parciais, informe quais partes você encontrou e quais estão faltando.
5. Forneça a resposta de forma clara, concisa e estruturada.
6. Quando aplicável, mencione o caminho de navegação para encontrar as informações no sistema original.

PERGUNTA DO USUÁRIO: {pergunta}
"""

        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        resposta = client.chat.completions.create(
            model=modelo_ia,
            messages=[
                {"role": "system", "content": "Você é um assistente especializado no sistema de Guia Rápido da Carglass que responde com base nos documentos fornecidos."},
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

# AQUIIIIIIIIIIIIIIIIIII Função para obter todos os documentos do SharePoint organizados por seção
def get_all_site_content(token):
    """Obtém todos os arquivos de todas as bibliotecas do site e organiza por seção"""
    documentos_por_secao = {
        "Operações": [],
        "Monitoria": [],
        "Treinamento": [],
        "Acesso Rápido": [],
        "Outros": []
    }
    
    estrutura_navegacao = {
        'categorias': {}, 
        'arvore_navegacao': {}
    }

    # Busca todas as bibliotecas do site
    bibliotecas = listar_bibliotecas(token)
    
    progresso = st.progress(0.0)
    st.text("Analisando bibliotecas...")
    
    # Para cada biblioteca, exploramos seu conteúdo
    for idx, biblioteca in enumerate(bibliotecas):
        drive_id = biblioteca.get("id")
        nome_biblioteca = biblioteca.get("name", "Sem Nome")
        
        if not drive_id:
            continue
            
        progress_value = (idx / len(bibliotecas))
        progresso.progress(progress_value)
        st.text(f"Processando biblioteca: {nome_biblioteca}")
        
        # Lista todos os arquivos dessa biblioteca, incluindo subpastas
        arquivos = listar_todos_os_arquivos(token, drive_id)
        
        for arq in arquivos:
            arq['_categoria'] = nome_biblioteca
            
            # Determina a seção com base no caminho da pasta e nome
            caminho = arq.get('_caminho_pasta', '/').lower()
            nome_arquivo = arq.get('name', '').lower()
            
            # Determina a seção através de várias regras
            secao = "Outros"
            
            # Regra 1: Baseada no caminho da pasta
            if "operacao" in caminho or "operações" in caminho or "operacoes" in caminho:
                secao = "Operações"
            elif "monitoria" in caminho:
                secao = "Monitoria"
            elif "treinamento" in caminho:
                secao = "Treinamento"
            elif "acesso" in caminho and "rapido" in caminho:
                secao = "Acesso Rápido"
            
            # Regra 2: Baseada no nome da biblioteca
            if "operacao" in nome_biblioteca.lower() or "operações" in nome_biblioteca.lower():
                secao = "Operações"
            elif "monitoria" in nome_biblioteca.lower():
                secao = "Monitoria"
            elif "treinamento" in nome_biblioteca.lower():
                secao = "Treinamento"
            elif "acesso" in nome_biblioteca.lower() and "rapido" in nome_biblioteca.lower():
                secao = "Acesso Rápido"
            
            # Regra 3: Baseada no nome do arquivo
            if "linha de frente" in nome_arquivo or "linha_de_frente" in nome_arquivo or "recontato" in nome_arquivo:
                if "vflr" in nome_arquivo:
                    secao = "Operações"
                elif "rrsm" in nome_arquivo:
                    secao = "Monitoria"
            
            # Regra 4: Verificar se é um comunicado
            if "comunicado" in nome_arquivo:
                if "linha" in caminho and "frente" in caminho:
                    secao = "Operações"
                elif "recontato" in caminho:
                    secao = "Monitoria"
            
            # Adiciona o arquivo à seção apropriada
            documentos_por_secao[secao].append(arq)
            
            # Atualiza estatísticas
            estrutura_navegacao['categorias'][nome_biblioteca] = estrutura_navegacao['categorias'].get(nome_biblioteca, 0) + 1
            
            # Constrói árvore de navegação
            caminho_navegacao = caminho.strip("/").split("/")
            arvore = estrutura_navegacao['arvore_navegacao']
            for parte in caminho_navegacao:
                if parte and parte not in arvore:
                    arvore[parte] = {}
                if parte:
                    arvore = arvore[parte]
    
    progresso.progress(1.0)
    st.text("Busca concluída!")
    
    # Armazena os resultados na session_state
    st.session_state['documentos_por_secao'] = documentos_por_secao
    st.session_state['estrutura_navegacao'] = estrutura_navegacao
    
    # Combina todos os documentos em uma única lista
    todos_documentos = []
    for docs in documentos_por_secao.values():
        todos_documentos.extend(docs)
    
    return todos_documentos
#AQUIIIIIIIIIIIIIIIIIIII
# Função para baixar múltiplos arquivos
def baixar_arquivos(token, arquivos, pasta="data", progress_bar=None, extensoes_validas=None):
    """Baixa múltiplos arquivos e retorna informações sobre eles"""
    # Define extensões padrão se não fornecidas
    if extensoes_validas is None:
        extensoes_validas = [".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".txt", ".docx"]
        
    # Filtra por extensões válidas
    arquivos_para_baixar = []
    for arq in arquivos:
        nome = arq.get("name", "").lower()
        if any(nome.endswith(ext) for ext in extensoes_validas):
            arquivos_para_baixar.append(arq)
    
    # Verifica se há arquivos para baixar
    total_arquivos = len(arquivos_para_baixar)
    if total_arquivos == 0:
        st.warning("⚠️ Nenhum arquivo com formato suportado encontrado.")
        return []
    
    # Lista para armazenar informações dos arquivos baixados
    arquivos_baixados = []
    
    # Download dos arquivos
    for i, arq in enumerate(arquivos_para_baixar):
        nome = arq.get("name", "")
        download_url = arq.get("@microsoft.graph.downloadUrl")
        nivel = arq.get("_nivel_hierarquico", 0)
        caminho = arq.get("_caminho_pasta", "/")
        categoria = arq.get("_categoria", "")
        
        if download_url:
            # Atualiza progresso
            if progress_bar:
                progresso = min((i + 1) / total_arquivos, 0.99)
                progress_bar.progress(progresso, text=f"Baixando {i+1}/{total_arquivos}: {nome}")
            
            # Baixa o arquivo
            caminho_local, conteudo_binario, caminho_pasta = baixar_arquivo(
                token, download_url, nome, caminho, pasta
            )
            
            if caminho_local:
                # Adiciona informações para cada arquivo baixado
                arquivo_info = {
                    "nome": nome,
                    "caminho_local": caminho_local,
                    "nivel_hierarquico": nivel,
                    "caminho_pasta": caminho,
                    "categoria": categoria
                }
                
                # Determina o tipo do arquivo
                if nome.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    arquivo_info["tipo"] = "imagem"
                elif nome.lower().endswith('.pdf'):
                    arquivo_info["tipo"] = "pdf"
                elif nome.lower().endswith(('.txt', '.csv')):
                    arquivo_info["tipo"] = "texto"
                else:
                    arquivo_info["tipo"] = "outro"
                
                arquivos_baixados.append(arquivo_info)
    
    # Finaliza progresso
    if progress_bar:
        progress_bar.progress(1.0, text=f"✅ Download concluído! {len(arquivos_baixados)}/{total_arquivos} arquivos baixados.")
        time.sleep(0.5)
    
    return arquivos_baixados

# Interface principal - só exibe se estiver autenticado
# Obter todos os documentos do SharePoint organizados por seção
if 'documentos_por_secao' not in st.session_state:
    with st.spinner("Conectando ao SharePoint e obtendo todos os documentos..."):
        try:
            # Usar a nova função para obter todos os documentos organizados por seção
            todos_documentos = get_all_site_content(token)
            
            # Verificar se foram encontrados documentos
            if not todos_documentos:
                st.warning("⚠️ Nenhum documento encontrado no SharePoint.")
            else:
                st.success(f"✅ Foram encontrados {len(todos_documentos)} documentos no SharePoint!")
                
                # Adicionar modo de depuração expandido
                with st.expander("🔍 Detalhes da Estrutura Encontrada", expanded=False):
                    estrutura = st.session_state.get('estrutura_navegacao', {})
                    
                    # Mostrar estatísticas
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Documentos por Seção")
                        for secao, docs in st.session_state.get('documentos_por_secao', {}).items():
                            st.info(f"{secao}: {len(docs)} documentos")
                    
                    with col2:
                        st.subheader("Documentos por Categoria")
                        categorias = estrutura.get('categorias', {})
                        for categoria, count in categorias.items():
                            st.info(f"{categoria}: {count} documentos")
                    
                    # Mostrar árvore de navegação
                    st.subheader("Árvore de Navegação")
                    st.json(estrutura.get('arvore_navegacao', {}))
        
        except Exception as e:
            st.error(f"❌ Erro ao obter documentos: {str(e)}")
            st.code(traceback.format_exc())

# Interface para selecionar seção, biblioteca e documentos
if 'documentos_por_secao' in st.session_state:
    # Obter todas as seções disponíveis
    secoes = list(st.session_state['documentos_por_secao'].keys())
    
    # Interface com abas para as seções principais
    if secoes:
        # Exibir as seções como tabs para melhor navegação
        tab_secoes = st.tabs(secoes)
        
        # Para cada seção, mostrar as bibliotecas e documentos
        for i, secao in enumerate(secoes):
            with tab_secoes[i]:
                st.header(f"📚 {secao}")
                
                # Obter documentos da seção atual
                documentos_secao = st.session_state['documentos_por_secao'][secao]
                
                # Agrupar por categoria ou biblioteca para melhor organização
                categorias = {}
                for doc in documentos_secao:
                    categoria = doc.get('_categoria', 'Geral')
                    if categoria not in categorias:
                        categorias[categoria] = []
                    categorias[categoria].append(doc)
                
                # Interface para selecionar documentos por categoria
                for categoria, docs in categorias.items():
                    with st.expander(f"{categoria} ({len(docs)} documentos)", expanded=True):
                        # Lista de documentos com checkbox para seleção
                        selected_docs = []
                        for doc in docs:
                            doc_name = doc.get('name', 'Documento sem nome')
                            doc_path = doc.get('_caminho_pasta', '/')
                            
                            # Cria um identificador único para o documento
                            doc_id = f"{doc_path}_{doc_name}"
                            
                            if st.checkbox(f"{doc_name}", key=doc_id):
                                selected_docs.append(doc)
                        
                        # Botão para processar os documentos selecionados
                        if selected_docs and st.button(f"🔍 Processar {len(selected_docs)} Documentos de {categoria}", key=f"btn_{secao}_{categoria}"):
                            with st.spinner(f"Baixando e extraindo texto de {len(selected_docs)} documento(s)..."):
                                # Baixar os documentos selecionados
                                arquivos_baixados = baixar_arquivos(
                                    token, 
                                    selected_docs, 
                                    pasta="data", 
                                    progress_bar=st.progress(0)
                                )
                                
                                if arquivos_baixados:
                                    st.success(f"✅ {len(arquivos_baixados)} documentos baixados com sucesso!")
                                    
                                    # Processar os arquivos baixados para extrair texto
                                    conteudo_extraido = []
                                    
                                    # Para cada arquivo baixado, extrair o texto
                                    for idx, arquivo in enumerate(arquivos_baixados):
                                        caminho_local = arquivo.get("caminho_local")
                                        tipo = arquivo.get("tipo")
                                        nome = arquivo.get("nome")
                                        nivel_hierarquico = arquivo.get("nivel_hierarquico", 0)
                                        caminho_pasta = arquivo.get("caminho_pasta", "/")
                                        
                                        st.text(f"Processando {idx+1}/{len(arquivos_baixados)}: {nome}")
                                        
                                        # Extrair texto do arquivo
                                        texto = extrair_texto_de_arquivo(
                                            caminho_local, 
                                            nome, 
                                            nivel_hierarquico, 
                                            caminho_pasta
                                        )
                                        
                                        if texto:
                                            conteudo_extraido.append(texto)
                                    
                                    # Salva na session_state
                                    st.session_state['conteudo_extraido'] = conteudo_extraido
                                    
                                    # Mostra amostra do texto extraído
                                    st.subheader("📝 Amostra do Texto Extraído")
                                    for idx, texto in enumerate(conteudo_extraido[:3]):  # Mostra apenas os 3 primeiros
                                        st.markdown(f"**Documento {idx+1}:**")
                                        if texto and len(texto) > 0:
                                            preview = texto[:500] + "..." if len(texto) > 500 else texto
                                            st.code(preview, language="text")
                                        else:
                                            st.info("Este documento não contém texto extraível.")
                                else:
                                    st.error("❌ Não foi possível baixar os documentos selecionados.")
    else:
        st.warning("Nenhuma seção encontrada no SharePoint.")

# Interface para perguntas e respostas
if 'conteudo_extraido' in st.session_state and st.session_state['conteudo_extraido']:
    st.header("🤖 Consulte o Oráculo")
    st.markdown("""
    Faça perguntas sobre os documentos e o Oráculo responderá com base no conteúdo extraído.
    
    **Exemplos de perguntas:**
    - Quais são os procedimentos para atendimento?
    - Como fazer a busca do cliente?
    - Qual o telefone de contato?
    - Quais assistências estão disponíveis?
    """)
    
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
            
            # Adiciona ao histórico
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

# Verificações diagnósticas
with st.expander("🔧 Diagnósticos", expanded=False):
    st.subheader("Verificação do Sistema")
    
    # Tesseract OCR
    try:
        versao = pytesseract.get_tesseract_version()
        st.success(f"✅ Tesseract OCR versão {versao} instalado e configurado.")
        
        try:
            idiomas = pytesseract.get_languages()
            st.info(f"Idiomas disponíveis: {', '.join(idiomas)}")
        except:
            st.warning("Não foi possível listar os idiomas disponíveis do Tesseract.")
    except Exception as e:
        st.error(f"❌ Tesseract OCR não encontrado ou não configurado: {str(e)}")
        st.info("""
        Para instalar o Tesseract OCR:
        
        **Windows:**
        1. Baixe o instalador em https://github.com/UB-Mannheim/tesseract/wiki
        2. Instale e adicione ao PATH
        
        **macOS:**
        ```bash
        brew install tesseract
        ```
        
        **Linux:**
        ```bash
        sudo apt update
        sudo apt install tesseract-ocr
        sudo apt install tesseract-ocr-por  # Para português
        ```
        """)
    
    # Processador de PDF
    st.subheader("Processamento de PDF")
    if pdf_processor == "pymupdf":
        st.success("✅ Usando PyMuPDF para processamento de PDFs (recomendado).")
    elif pdf_processor == "pdf2image":
        try:
            pdf2image.pdfinfo_from_bytes(b"%PDF-1.0\n1 0 obj<</Pages 2 0 R>>/endobj/trailer<</Root 1 0 R>>")
            st.success("✅ Poppler está instalado e configurado corretamente.")
        except Exception as e:
            st.error(f"❌ Poppler não está configurado corretamente: {str(e)}")
            st.info("""
            Para instalar o Poppler:
            
            **Windows:**
            1. Baixe em https://github.com/oschwartz10612/poppler-windows/releases/
            2. Extraia e adicione a pasta bin ao PATH
            
            **macOS:**
            ```bash
            brew install poppler
            ```
            
            **Linux:**
            ```bash
            sudo apt install poppler-utils
            ```
            
            **Streamlit Cloud:**
            Crie um arquivo packages.txt na raiz do projeto com o conteúdo:
            ```
            poppler-utils
            ```
            """)
    else:
        st.error("❌ Nenhum processador de PDF disponível.")
    
    # Python-magic (opcional)
    st.subheader("Detecção de Tipo de Arquivo")
    if has_magic:
        st.success("✅ Python-magic está instalado para melhor detecção de tipo de arquivo.")
    else:
        st.warning("⚠️ Python-magic não está instalado. A detecção de tipo de arquivo será limitada à extensão.")
        st.info("""
        Para instalar python-magic:
        
        ```bash
        pip install python-magic
        ```
        
        No Windows também é necessário:
        ```bash
        pip install python-magic-bin
        ```
        """)

# Rodapé
st.markdown("---")
st.markdown(
    """<div style="text-align: center; color: #666;">
    <p>🔮 Oráculo - Análise Inteligente de Documentos do SharePoint</p>
    <p style="font-size: 0.8em;">Desenvolvido para análise hierárquica do Guia Rápido da Carglass.</p>
    </div>""",
    unsafe_allow_html=True
)
