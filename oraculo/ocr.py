"""
Módulo de OCR (Reconhecimento Óptico de Caracteres) para extrair texto de imagens e PDFs.
Adaptado para tratar estrutura hierárquica de menus e botões do Guia Rápido da Carglass.
"""

import os
import io
import tempfile
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import numpy as np
from typing import List, Optional, Union, Tuple, Dict, Any

def pre_processar_imagem(
    img: Image.Image, 
    aumentar_contraste: bool = True,
    escala_cinza: bool = True,
    nitidez: bool = True,
    remover_ruido: bool = True,
    binarizacao: bool = False
) -> Image.Image:
    """
    Aplica técnicas de pré-processamento para melhorar a qualidade do OCR.
    
    Args:
        img: Objeto PIL Image
        aumentar_contraste: Se deve aumentar o contraste
        escala_cinza: Se deve converter para escala de cinza
        nitidez: Se deve aumentar a nitidez
        remover_ruido: Se deve remover ruído
        binarizacao: Se deve aplicar binarização
        
    Returns:
        Imagem processada
    """
    # Converte para RGB se tiver canal alpha
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    # Converte para escala de cinza
    if escala_cinza:
        img = img.convert('L')
    
    # Aumenta o contraste
    if aumentar_contraste:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
    
    # Remove ruído
    if remover_ruido:
        img = img.filter(ImageFilter.MedianFilter(size=3))
    
    # Aumenta nitidez
    if nitidez:
        img = img.filter(ImageFilter.SHARPEN)
    
    # Binarização adaptativa (preto e branco)
    if binarizacao:
        # Limiarização simples
        fn = lambda x: 255 if x > 128 else 0
        img = img.convert('L').point(fn, mode='1')
    
    return img

def detectar_botoes_e_menus(img: Image.Image) -> List[Dict[str, Any]]:
    """
    Tenta detectar botões e elementos de menu em uma imagem.
    
    Args:
        img: Objeto PIL Image
        
    Returns:
        Lista de dicionários com informações sobre botões detectados
    """
    # Converte para array numpy para processamento
    img_array = np.array(img)
    botoes_detectados = []
    
    # Implementação simples: detecta retângulos por segmentação de cor
    # Isso funciona melhor para botões com cores específicas como observado nas imagens
    
    # Converte para HSV para melhor segmentação de cor
    try:
        import cv2
        img_rgb = img.convert('RGB')
        img_np = np.array(img_rgb)
        img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
        
        # Ranges de cor para botões amarelos (como observado nas capturas)
        lower_yellow = np.array([20, 100, 100])
        upper_yellow = np.array([40, 255, 255])
        mask_yellow = cv2.inRange(img_hsv, lower_yellow, upper_yellow)
        
        # Encontra contornos
        contours, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Processa cada contorno encontrado
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filtra por tamanho
            if w > 50 and h > 20:  # Tamanho mínimo para ser um botão
                # Recorta a região do botão e extrai texto
                roi = img.crop((x, y, x+w, y+h))
                texto = pytesseract.image_to_string(roi, lang="por").strip()
                
                if texto:
                    botoes_detectados.append({
                        "texto": texto,
                        "x": x,
                        "y": y,
                        "largura": w,
                        "altura": h
                    })
    except:
        # Se opencv não estiver disponível ou ocorrer outro erro
        pass
    
    return botoes_detectados

def extrair_texto_de_imagem(
    img_data_or_path: Union[str, bytes, Image.Image],
    idioma: str = "por+eng",
    pre_processamento: bool = True,
    config_tesseract: str = "--psm 3",
    detectar_menus: bool = True,
    nivel_hierarquico: int = 0,
    caminho_pasta: str = "/"
) -> str:
    """
    Extrai texto de uma imagem usando OCR, com consciência de estrutura hierárquica.
    
    Args:
        img_data_or_path: Caminho do arquivo, bytes ou objeto PIL Image
        idioma: Código do idioma para o Tesseract
        pre_processamento: Se deve aplicar técnicas de pré-processamento
        config_tesseract: Configurações adicionais para o Tesseract
        detectar_menus: Se deve tentar detectar botões e menus na imagem
        nivel_hierarquico: Nível hierárquico do documento
        caminho_pasta: Caminho da pasta no SharePoint
        
    Returns:
        Texto extraído da imagem com informações de contexto
    """
    try:
        # Carrega a imagem dependendo do tipo de entrada
        if isinstance(img_data_or_path, str):
            # Caminho do arquivo
            if not os.path.exists(img_data_or_path):
                return "[erro: arquivo não encontrado]"
            img = Image.open(img_data_or_path)
            nome_arquivo = os.path.basename(img_data_or_path)
        elif isinstance(img_data_or_path, bytes):
            # Dados binários
            img = Image.open(io.BytesIO(img_data_or_path))
            nome_arquivo = "arquivo_binario.png"
        elif isinstance(img_data_or_path, Image.Image):
            # Já é um objeto PIL Image
            img = img_data_or_path
            nome_arquivo = "imagem.png"
        else:
            return "[erro: formato de entrada inválido]"
        
        # Aplica pré-processamento
        if pre_processamento:
            img_processada = pre_processar_imagem(img)
        else:
            img_processada = img
        
        # Extrai o texto usando pytesseract
        texto = pytesseract.image_to_string(img_processada, lang=idioma, config=config_tesseract)
        
        # Limpa o texto e remove caracteres problemáticos
        texto = texto.strip()
        
        # Detecta botões e menus
        elementos_interface = []
        if detectar_menus:
            botoes = detectar_botoes_e_menus(img)
            if botoes:
                elementos_interface.append("\n\nElementos de interface detectados:")
                for i, botao in enumerate(botoes):
                    elementos_interface.append(f"- Botão {i+1}: '{botao['texto']}'")
        
        # Adiciona informações de contexto hierárquico
        contexto = []
        if nivel_hierarquico > 0:
            contexto.append(f"[Nível {nivel_hierarquico}]")
        
        if caminho_pasta and caminho_pasta != "/":
            contexto.append(f"[Caminho: {caminho_pasta}]")
        
        # Identifica tipo de conteúdo com base no nome do arquivo ou texto
        if "guia" in nome_arquivo.lower():
            contexto.append("[Tipo: Guia]")
        elif "comunicado" in nome_arquivo.lower() or "comunicado" in texto.lower():
            contexto.append("[Tipo: Comunicado]")
        
        # Tenta identificar menus e categorias
        if "guia rápido" in texto.lower():
            contexto.append("[Menu: Guia Rápido]")
        elif "assistências" in texto.lower() or "assistencias" in texto.lower():
            contexto.append("[Categoria: Assistências]")
        elif "seguros" in texto.lower() or "seguradoras" in texto.lower():
            contexto.append("[Categoria: Seguros]")
        
    # Adiciona a informação hierárquica ao texto
        if contexto:
            texto = " ".join(contexto) + "\n\n" + texto
        
        # Adiciona informações sobre elementos de interface detectados
        if elementos_interface:
            texto += "\n" + "\n".join(elementos_interface)
        
        # Retorna o resultado ou uma mensagem de erro
        return texto if texto else "[imagem sem texto legível]"
    
    except Exception as e:
        st.error(f"Erro ao processar imagem com OCR: {str(e)}")
        return f"[erro ao processar imagem: {str(e)}]"

def extrair_texto_de_pdf(
    pdf_data_or_path: Union[str, bytes],
    idioma: str = "por+eng",
    paginas: Optional[List[int]] = None,
    dpi: int = 300,
    pre_processamento: bool = True,
    nivel_hierarquico: int = 0,
    caminho_pasta: str = "/"
) -> str:
    """
    Extrai texto de um PDF utilizando OCR em cada página.
    Adaptado para estrutura hierárquica.
    
    Args:
        pdf_data_or_path: Caminho do arquivo ou dados binários do PDF
        idioma: Código do idioma para o Tesseract
        paginas: Lista de números de páginas para processar (None = todas)
        dpi: Resolução para conversão do PDF em imagens
        pre_processamento: Se deve aplicar técnicas de pré-processamento
        nivel_hierarquico: Nível hierárquico do documento
        caminho_pasta: Caminho da pasta no SharePoint
        
    Returns:
        Texto extraído de todas as páginas com informações de contexto
    """
    try:
        # Determina o nome do arquivo para análise de contexto
        if isinstance(pdf_data_or_path, str):
            nome_arquivo = os.path.basename(pdf_data_or_path)
        else:
            nome_arquivo = "arquivo.pdf"
        
        # Cria arquivo temporário se a entrada for dados binários
        if isinstance(pdf_data_or_path, bytes):
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf.write(pdf_data_or_path)
                temp_pdf_path = temp_pdf.name
        else:
            # Verifica se o arquivo existe
            if not os.path.exists(pdf_data_or_path):
                return "[erro: arquivo PDF não encontrado]"
            temp_pdf_path = pdf_data_or_path
        
        # Tenta importar bibliotecas necessárias
        try:
            # Tenta primeiro com PyMuPDF (mais rápido e sem dependência do Poppler)
            import fitz
            return extrair_texto_de_pdf_com_pymupdf(
                temp_pdf_path, 
                nivel_hierarquico=nivel_hierarquico, 
                caminho_pasta=caminho_pasta, 
                nome_arquivo=nome_arquivo
            )
        except ImportError:
            try:
                # Tenta com pdf2image (requer Poppler)
                import pdf2image
                return extrair_texto_de_pdf_com_pdf2image(
                    temp_pdf_path, 
                    idioma=idioma,
                    paginas=paginas,
                    dpi=dpi, 
                    pre_processamento=pre_processamento,
                    nivel_hierarquico=nivel_hierarquico,
                    caminho_pasta=caminho_pasta,
                    nome_arquivo=nome_arquivo
                )
            except ImportError:
                # Se ambos falharem, tenta processar diretamente como imagem
                return f"[erro: nenhuma biblioteca de processamento de PDF está disponível]"
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return f"[erro ao processar PDF: {str(e)}]"

def extrair_texto_de_pdf_com_pymupdf(
    pdf_path: str,
    nivel_hierarquico: int = 0,
    caminho_pasta: str = "/",
    nome_arquivo: str = "arquivo.pdf"
) -> str:
    """
    Extrai texto de um PDF usando PyMuPDF (fitz).
    Adaptado para estrutura hierárquica.
    
    Args:
        pdf_path: Caminho do arquivo PDF
        nivel_hierarquico: Nível hierárquico do documento
        caminho_pasta: Caminho da pasta no SharePoint
        nome_arquivo: Nome do arquivo para contexto
        
    Returns:
        Texto extraído com informações de contexto
    """
    try:
        import fitz  # PyMuPDF
        
        # Abre o documento
        doc = fitz.open(pdf_path)
        
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
                texto_ocr = extrair_texto_de_imagem(
                    img, 
                    nivel_hierarquico=nivel_hierarquico,
                    caminho_pasta=caminho_pasta
                )
                
                if texto_ocr and texto_ocr != "[imagem sem texto legível]":
                    textos.append(f"--- Página {i+1} (OCR) ---\n{texto_ocr}")
        
        # Combina o texto de todas as páginas
        texto_combinado = "\n\n".join(textos) if textos else "[PDF sem texto legível]"
        
        # Adiciona informações de contexto hierárquico
        contexto = []
        if nivel_hierarquico > 0:
            contexto.append(f"[Nível {nivel_hierarquico}]")
        
        if caminho_pasta and caminho_pasta != "/":
            contexto.append(f"[Caminho: {caminho_pasta}]")
        
        # Identifica tipo de conteúdo com base no nome do arquivo ou texto
        if "guia" in nome_arquivo.lower():
            contexto.append("[Tipo: Guia]")
        elif "comunicado" in nome_arquivo.lower() or "comunicado" in texto_combinado.lower():
            contexto.append("[Tipo: Comunicado]")
        
        # Tenta identificar menus e categorias
        if "guia rápido" in texto_combinado.lower():
            contexto.append("[Menu: Guia Rápido]")
        elif "assistências" in texto_combinado.lower() or "assistencias" in texto_combinado.lower():
            contexto.append("[Categoria: Assistências]")
        elif "seguros" in texto_combinado.lower() or "seguradoras" in texto_combinado.lower():
            contexto.append("[Categoria: Seguros]")
        
        # Adiciona a informação hierárquica ao texto
        if contexto:
            texto_combinado = " ".join(contexto) + "\n\n" + texto_combinado
        
        return texto_combinado
        
    except Exception as e:
        return f"[erro ao processar PDF com PyMuPDF: {str(e)}]"

def extrair_texto_de_pdf_com_pdf2image(
    pdf_path: str,
    idioma: str = "por+eng",
    paginas: Optional[List[int]] = None,
    dpi: int = 300,
    pre_processamento: bool = True,
    nivel_hierarquico: int = 0,
    caminho_pasta: str = "/",
    nome_arquivo: str = "arquivo.pdf"
) -> str:
    """
    Extrai texto de um PDF usando pdf2image e OCR.
    Adaptado para estrutura hierárquica.
    
    Args:
        pdf_path: Caminho do arquivo PDF
        idioma: Código do idioma para o Tesseract
        paginas: Lista de números de páginas para processar (None = todas)
        dpi: Resolução para conversão do PDF em imagens
        pre_processamento: Se deve aplicar técnicas de pré-processamento
        nivel_hierarquico: Nível hierárquico do documento
        caminho_pasta: Caminho da pasta no SharePoint
        nome_arquivo: Nome do arquivo para contexto
        
    Returns:
        Texto extraído com informações de contexto
    """
    try:
        import pdf2image
        
        # Cria uma pasta temporária para as imagens extraídas
        with tempfile.TemporaryDirectory() as temp_dir:
            # Converte o PDF em imagens
            try:
                imagens = pdf2image.convert_from_path(
                    pdf_path, 
                    dpi=dpi,
                    first_page=paginas[0] if paginas else None,
                    last_page=paginas[-1] if paginas else None,
                    output_folder=temp_dir,
                    fmt="jpeg",
                    thread_count=4,  # Usa múltiplos threads para acelerar
                    grayscale=pre_processamento
                )
            except Exception as e:
                # Se falhar na conversão, pode ser um problema com o Poppler
                if "Unable to get page count" in str(e):
                    return f"[erro com Poppler: {str(e)}]"
                return f"[erro ao converter PDF para imagens: {str(e)}]"
            
            # Extrai texto de cada página
            textos = []
            num_paginas = len(imagens)
            
            for i, img in enumerate(imagens):
                # Atualiza progresso, se estiver no Streamlit
                if hasattr(st, 'progress') and num_paginas > 1:
                    progresso = (i + 1) / num_paginas
                    placeholder = st.empty()
                    placeholder.text(f"Processando página {i+1}/{num_paginas}...")
                
                # Aplica OCR na imagem
                texto_pagina = extrair_texto_de_imagem(
                    img, 
                    idioma=idioma,
                    pre_processamento=pre_processamento,
                    nivel_hierarquico=nivel_hierarquico,
                    caminho_pasta=caminho_pasta
                )
                
                if texto_pagina and texto_pagina != "[imagem sem texto legível]":
                    textos.append(f"--- Página {i+1} ---\n{texto_pagina}")
                
                # Limpa o placeholder
                if hasattr(st, 'progress') and num_paginas > 1:
                    placeholder.empty()
            
            # Combina o texto de todas as páginas
            texto_combinado = "\n\n".join(textos) if textos else "[PDF sem texto legível]"
            
            # Adiciona informações de contexto hierárquico
            contexto = []
            if nivel_hierarquico > 0:
                contexto.append(f"[Nível {nivel_hierarquico}]")
            
            if caminho_pasta and caminho_pasta != "/":
                contexto.append(f"[Caminho: {caminho_pasta}]")
            
            # Identifica tipo de conteúdo com base no nome do arquivo ou texto
            if "guia" in nome_arquivo.lower():
                contexto.append("[Tipo: Guia]")
            elif "comunicado" in nome_arquivo.lower() or "comunicado" in texto_combinado.lower():
                contexto.append("[Tipo: Comunicado]")
            
            # Tenta identificar menus e categorias
            if "guia rápido" in texto_combinado.lower():
                contexto.append("[Menu: Guia Rápido]")
            elif "assistências" in texto_combinado.lower() or "assistencias" in texto_combinado.lower():
                contexto.append("[Categoria: Assistências]")
            elif "seguros" in texto_combinado.lower() or "seguradoras" in texto_combinado.lower():
                contexto.append("[Categoria: Seguros]")
            
            # Adiciona a informação hierárquica ao texto
            if contexto:
                texto_combinado = " ".join(contexto) + "\n\n" + texto_combinado
            
            return texto_combinado
    
    except Exception as e:
        return f"[erro ao processar PDF com pdf2image: {str(e)}]"

def extrair_texto_de_arquivo(
    caminho_ou_conteudo: Union[str, bytes],
    nome_arquivo: Optional[str] = None,
    idioma: str = "por+eng",
    nivel_hierarquico: int = 0,
    caminho_pasta: str = "/"
) -> str:
    """
    Extrai texto de um arquivo baseado em sua extensão.
    Adaptado para estrutura hierárquica.
    
    Args:
        caminho_ou_conteudo: Caminho para o arquivo ou dados binários
        nome_arquivo: Nome do arquivo (necessário se passar dados binários)
        idioma: Código do idioma para o OCR
        nivel_hierarquico: Nível hierárquico do documento
        caminho_pasta: Caminho da pasta no SharePoint
        
    Returns:
        Texto extraído do arquivo com informações de contexto
    """
    # Determina a extensão e nome do arquivo
    if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
        nome = os.path.basename(caminho_ou_conteudo).lower()
    else:
        nome = nome_arquivo.lower() if nome_arquivo else ""
    
    # Tenta detectar o tipo MIME do arquivo
    mime_type = None
    try:
        import magic
        if isinstance(caminho_ou_conteudo, bytes):
            mime_type = magic.from_buffer(caminho_ou_conteudo, mime=True)
        elif isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
            mime_type = magic.from_file(caminho_ou_conteudo, mime=True)
    except:
        pass
    
    # Processa baseado no tipo MIME ou extensão
    if mime_type:
        if 'image' in mime_type:
            return extrair_texto_de_imagem(
                caminho_ou_conteudo, 
                idioma=idioma,
                nivel_hierarquico=nivel_hierarquico,
                caminho_pasta=caminho_pasta
            )
        elif 'pdf' in mime_type:
            return extrair_texto_de_pdf(
                caminho_ou_conteudo, 
                idioma=idioma,
                nivel_hierarquico=nivel_hierarquico,
                caminho_pasta=caminho_pasta
            )
        elif 'text' in mime_type:
            # Extrai texto direto
            if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
                with open(caminho_ou_conteudo, 'r', encoding='utf-8', errors='ignore') as f:
                    texto = f.read()
            elif isinstance(caminho_ou_conteudo, bytes):
                texto = caminho_ou_conteudo.decode('utf-8', errors='ignore')
            else:
                return f"[formato de arquivo não suportado]"
            
            # Adiciona informações de contexto
            contexto = []
            if nivel_hierarquico > 0:
                contexto.append(f"[Nível {nivel_hierarquico}]")
            
            if caminho_pasta and caminho_pasta != "/":
                contexto.append(f"[Caminho: {caminho_pasta}]")
            
            if contexto:
                texto = " ".join(contexto) + "\n\n" + texto
            
            return texto
    else:
        # Determina o tipo baseado na extensão
        if nome.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
            return extrair_texto_de_imagem(
                caminho_ou_conteudo, 
                idioma=idioma,
                nivel_hierarquico=nivel_hierarquico,
                caminho_pasta=caminho_pasta
            )
        elif nome.endswith('.pdf'):
            return extrair_texto_de_pdf(
                caminho_ou_conteudo, 
                idioma=idioma,
                nivel_hierarquico=nivel_hierarquico,
                caminho_pasta=caminho_pasta
            )
        elif nome.endswith(('.txt', '.csv', '.md', '.html', '.xml')):
            # Extrai texto direto
            if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
                with open(caminho_ou_conteudo, 'r', encoding='utf-8', errors='ignore') as f:
                    texto = f.read()
            elif isinstance(caminho_ou_conteudo, bytes):
                texto = caminho_ou_conteudo.decode('utf-8', errors='ignore')
            else:
                return f"[formato de arquivo não suportado]"
            
            # Adiciona informações de contexto
            contexto = []
            if nivel_hierarquico > 0:
                contexto.append(f"[Nível {nivel_hierarquico}]")
            
            if caminho_pasta and caminho_pasta != "/":
                contexto.append(f"[Caminho: {caminho_pasta}]")
            
            if contexto:
                texto = " ".join(contexto) + "\n\n" + texto
            
            return texto
        else:
            # Para arquivos desconhecidos, tenta primeiro como imagem
            try:
                return extrair_texto_de_imagem(
                    caminho_ou_conteudo, 
                    idioma=idioma,
                    nivel_hierarquico=nivel_hierarquico,
                    caminho_pasta=caminho_pasta
                )
            except:
                pass
            
            # Se falhar, tenta como PDF
            try:
                return extrair_texto_de_pdf(
                    caminho_ou_conteudo, 
                    idioma=idioma,
                    nivel_hierarquico=nivel_hierarquico,
                    caminho_pasta=caminho_pasta
                )
            except:
                pass
    
    # Se todas as tentativas falharem
    return f"[não foi possível extrair texto do formato: {nome}]"

def verificar_tesseract() -> Tuple[bool, str]:
    """
    Verifica se o Tesseract OCR está instalado e disponível.
    
    Returns:
        Tupla (instalado, mensagem)
    """
    try:
        versao = pytesseract.get_tesseract_version()
        return True, f"Tesseract OCR v{versao} instalado e funcionando."
    except Exception as e:
        return False, f"Tesseract OCR não encontrado ou não configurado: {str(e)}"

def listar_idiomas_tesseract() -> List[str]:
    """
    Lista os idiomas disponíveis no Tesseract OCR.
    
    Returns:
        Lista de códigos de idiomas instalados
    """
    try:
        return pytesseract.get_languages()
    except:
        return ["eng"]  # Retorna inglês como padrão em caso de erro

def extrair_info_contexto(texto: str) -> Dict[str, Any]:
    """
    Extrai informações de contexto de textos processados.
    
    Args:
        texto: Texto processado com marcações de contexto
        
    Returns:
        Dicionário com informações de contexto extraídas
    """
    nivel = 0
    caminho = "/"
    tipo = "Desconhecido"
    menu = ""
    categoria = ""
    
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
    
    if "[Categoria: " in texto:
        try:
            categoria = texto.split("[Categoria: ")[1].split("]")[0]
        except:
            pass
    
    # Extrai palavras-chave relevantes do texto
    texto_lower = texto.lower()
    palavras_chave = []
    
    termos_importantes = [
        "comunicado", "guia rápido", "assistência", "seguros", 
        "atendimento", "procedimento", "telefone", "contato",
        "reembolso", "fluxo", "busca", "cliente"
    ]
    
    for termo in termos_importantes:
        if termo in texto_lower:
            palavras_chave.append(termo)
    
    return {
        "nivel": nivel,
        "caminho": caminho,
        "tipo": tipo,
        "menu": menu,
        "categoria": categoria,
        "palavras_chave": palavras_chave
    }
