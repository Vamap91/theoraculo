"""
Módulo de OCR (Reconhecimento Óptico de Caracteres) para extrair texto de imagens e PDFs.
Utiliza Tesseract OCR e outras ferramentas para processamento de documentos visuais.
"""

import os
import io
import tempfile
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import pdf2image
from typing import List, Optional, Union, Tuple, Dict

def pre_processar_imagem(
    img: Image.Image, 
    aumentar_contraste: bool = True,
    escala_cinza: bool = True,
    nitidez: bool = True,
    binarizacao: bool = False,
    remover_ruido: bool = True
) -> Image.Image:
    """
    Aplica técnicas de pré-processamento para melhorar a qualidade do OCR.
    
    Args:
        img: Objeto PIL Image
        aumentar_contraste: Se deve aumentar o contraste
        escala_cinza: Se deve converter para escala de cinza
        nitidez: Se deve aumentar a nitidez
        binarizacao: Se deve aplicar binarização
        remover_ruido: Se deve remover ruído
        
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

def extrair_texto_de_imagem(
    img_data_or_path: Union[str, bytes, Image.Image],
    idioma: str = "por+eng",
    pre_processamento: bool = True,
    config_tesseract: str = "--psm 3"
) -> str:
    """
    Extrai texto de uma imagem usando OCR.
    
    Args:
        img_data_or_path: Caminho do arquivo, bytes ou objeto PIL Image
        idioma: Código do idioma para o Tesseract
        pre_processamento: Se deve aplicar técnicas de pré-processamento
        config_tesseract: Configurações adicionais para o Tesseract
        
    Returns:
        Texto extraído da imagem
    """
    try:
        # Carrega a imagem dependendo do tipo de entrada
        if isinstance(img_data_or_path, str):
            # Caminho do arquivo
            if not os.path.exists(img_data_or_path):
                return "[erro: arquivo não encontrado]"
            img = Image.open(img_data_or_path)
        elif isinstance(img_data_or_path, bytes):
            # Dados binários
            img = Image.open(io.BytesIO(img_data_or_path))
        elif isinstance(img_data_or_path, Image.Image):
            # Já é um objeto PIL Image
            img = img_data_or_path
        else:
            return "[erro: formato de entrada inválido]"
        
        # Aplica pré-processamento
        if pre_processamento:
            img = pre_processar_imagem(img)
        
        # Extrai o texto usando pytesseract
        texto = pytesseract.image_to_string(img, lang=idioma, config=config_tesseract)
        
        # Limpa o texto e remove caracteres problemáticos
        texto = texto.strip()
        
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
    pre_processamento: bool = True
) -> str:
    """
    Extrai texto de um PDF utilizando OCR em cada página.
    
    Args:
        pdf_data_or_path: Caminho do arquivo ou dados binários do PDF
        idioma: Código do idioma para o Tesseract
        paginas: Lista de números de páginas para processar (None = todas)
        dpi: Resolução para conversão do PDF em imagens
        pre_processamento: Se deve aplicar técnicas de pré-processamento
        
    Returns:
        Texto extraído de todas as páginas
    """
    try:
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
        
        # Converte o PDF em imagens
        try:
            imagens = pdf2image.convert_from_path(
                temp_pdf_path, 
                dpi=dpi,
                first_page=paginas[0] if paginas else None,
                last_page=paginas[-1] if paginas else None
            )
        except Exception as e:
            return f"[erro ao converter PDF para imagens: {str(e)}]"
        
        # Remove o arquivo temporário se foi criado
        if isinstance(pdf_data_or_path, bytes):
            os.unlink(temp_pdf_path)
        
        # Extrai texto de cada página
        textos = []
        
        # Usa apenas as páginas especificadas ou todas
        paginas_para_processar = paginas if paginas else range(len(imagens))
        
        for i, img in enumerate(imagens):
            # Verifica se esta página deve ser processada
            if paginas and i+1 not in paginas:
                continue
                
            # Aplica OCR na imagem da página
            texto_pagina = extrair_texto_de_imagem(
                img, 
                idioma=idioma,
                pre_processamento=pre_processamento
            )
            
            if texto_pagina and texto_pagina != "[imagem sem texto legível]":
                textos.append(f"--- Página {i+1} ---\n{texto_pagina}")
        
        # Combina o texto de todas as páginas
        texto_completo = "\n\n".join(textos)
        
        # Retorna o resultado ou uma mensagem de erro
        return texto_completo if texto_completo else "[PDF sem texto legível]"
    
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return f"[erro ao processar PDF: {str(e)}]"

def extrair_texto_de_arquivo(
    caminho_ou_conteudo: Union[str, bytes],
    nome_arquivo: Optional[str] = None,
    idioma: str = "por+eng"
) -> str:
    """
    Extrai texto de um arquivo baseado em sua extensão.
    
    Args:
        caminho_ou_conteudo: Caminho para o arquivo ou dados binários
        nome_arquivo: Nome do arquivo (necessário se passar dados binários)
        idioma: Código do idioma para o OCR
        
    Returns:
        Texto extraído do arquivo
    """
    # Determina a extensão
    if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
        nome = caminho_ou_conteudo.lower()
    else:
        nome = nome_arquivo.lower() if nome_arquivo else ""
    
    # Verifica se o formato é suportado
    if nome.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
        return extrair_texto_de_imagem(caminho_ou_conteudo, idioma=idioma)
    elif nome.endswith('.pdf'):
        return extrair_texto_de_pdf(caminho_ou_conteudo, idioma=idioma)
    elif nome.endswith(('.txt', '.csv', '.md', '.html', '.xml')):
        # Trata arquivos de texto
        if isinstance(caminho_ou_conteudo, str) and os.path.exists(caminho_ou_conteudo):
            try:
                with open(caminho_ou_conteudo, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                return f"[erro ao ler arquivo de texto: {str(e)}]"
        elif isinstance(caminho_ou_conteudo, bytes):
            try:
                return caminho_ou_conteudo.decode('utf-8', errors='ignore')
            except Exception as e:
                return f"[erro ao decodificar arquivo de texto: {str(e)}]"
    
    # Formato não suportado
    return f"[formato de arquivo não suportado: {nome}]"

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
