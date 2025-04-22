"""
Módulo de busca e download de arquivos do SharePoint via Microsoft Graph API.
Fornece funções para listar bibliotecas, navegar pastas e baixar arquivos.
"""

import os
import requests
import time
import streamlit as st
from typing import List, Dict, Optional, Tuple, Any, Union

# Configurações da API
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
SITE_ID = "carglassbr.sharepoint.com,7d0ecc3f-b6c8-411d-8ae4-6d5679a38ca8,e53fc2d9-95b5-4675-813d-769b7a737286"

def listar_bibliotecas(token: str) -> List[Dict[str, Any]]:
    """
    Lista todas as bibliotecas de documentos do SharePoint.
    
    Args:
        token: Token de autenticação para a Microsoft Graph API
        
    Returns:
        Lista de dicionários com informações das bibliotecas
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/sites/{SITE_ID}/drives"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Levanta exceção para códigos de erro HTTP
        return response.json().get("value", [])
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Erro ao listar bibliotecas: {str(e)}")
        if hasattr(e, 'response') and e.response:
            st.code(e.response.text)
        return []

def listar_pastas(token: str, drive_id: str, folder_path: str = "/") -> List[Dict[str, Any]]:
    """
    Lista apenas as pastas em um caminho específico.
    
    Args:
        token: Token de autenticação
        drive_id: ID da biblioteca do SharePoint
        folder_path: Caminho relativo da pasta
        
    Returns:
        Lista de pastas no caminho especificado
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
        response.raise_for_status()
        
        # Filtra apenas itens que são pastas
        items = response.json().get("value", [])
        return [item for item in items if item.get("folder")]
        
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro ao listar pastas em {folder_path}: {str(e)}")
        return []

def listar_arquivos(token: str, drive_id: str, folder_path: str = "/") -> List[Dict[str, Any]]:
    """
    Lista apenas os arquivos (não pastas) em um caminho específico.
    
    Args:
        token: Token de autenticação
        drive_id: ID da biblioteca do SharePoint
        folder_path: Caminho relativo da pasta
        
    Returns:
        Lista de arquivos no caminho especificado
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
        response.raise_for_status()
        
        # Filtra apenas itens que NÃO são pastas
        items = response.json().get("value", [])
        return [item for item in items if not item.get("folder")]
        
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro ao listar arquivos em {folder_path}: {str(e)}")
        return []

def listar_todos_os_arquivos(
    token: str, 
    drive_id: str, 
    caminho_pasta: str = "/", 
    progress_bar: Optional[Any] = None,
    progress_start: float = 0.0,
    progress_end: float = 1.0,
    nivel_atual: int = 0,
    limite: Optional[int] = None,
    filtrar_extensoes: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Lista todos os arquivos recursivamente, incluindo em subpastas.
    
    Args:
        token: Token de autenticação
        drive_id: ID da biblioteca
        caminho_pasta: Caminho da pasta atual
        progress_bar: Objeto de barra de progresso do Streamlit
        progress_start: Valor inicial da barra de progresso para este nível
        progress_end: Valor final da barra de progresso para este nível
        nivel_atual: Nível de recursão atual
        limite: Número máximo de arquivos a retornar
        filtrar_extensoes: Lista de extensões de arquivo para filtrar
        
    Returns:
        Lista de arquivos encontrados
    """
    headers = {"Authorization": f"Bearer {token}"}
    
    # Normaliza o caminho da pasta
    if caminho_pasta == "/":
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root/children"
    else:
        # Remove barras duplas e garante formato correto
        caminho_pasta = caminho_pasta.replace("//", "/")
        if caminho_pasta.startswith("/"):
            caminho_pasta = caminho_pasta[1:]
        url = f"{GRAPH_ROOT}/drives/{drive_id}/root:/{caminho_pasta}:/children"
    
    arquivos = []
    try:
        # Adiciona parâmetro de paginação e ordenação
        params = {
            "$top": 1000,  # Número máximo de itens por página
            "$orderby": "name asc"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        itens = response.json().get("value", [])
        total_itens = len(itens)
        
        # Atualiza o status na barra de progresso
        if progress_bar and nivel_atual == 0:
            progress_bar.progress(
                progress_start + 0.1 * (progress_end - progress_start),
                text=f"Encontrados {total_itens} itens em {caminho_pasta or '/'}"
            )
        
        # Processa cada item (arquivo ou pasta)
        for i, item in enumerate(itens):
            # Verifica se atingiu o limite de arquivos
            if limite and len(arquivos) >= limite:
                break
            
            # Calcula o progresso atual
            if progress_bar and nivel_atual == 0:
                current_progress = progress_start + (progress_end - progress_start) * (i / total_itens)
                progress_bar.progress(
                    min(current_progress, progress_end),
                    text=f"Processando {i+1}/{total_itens} em {caminho_pasta or '/'}"
                )
            
            # Se for uma pasta, busca recursivamente
            if item.get("folder"):
                nova_pasta = f"{caminho_pasta}/{item['name']}".replace("//", "/")
                
                # Define a porção do progresso para esta subpasta
                if progress_bar and nivel_atual == 0:
                    sub_start = progress_start + (progress_end - progress_start) * (i / total_itens)
                    sub_end = progress_start + (progress_end - progress_start) * ((i + 1) / total_itens)
                else:
                    sub_start = progress_start
                    sub_end = progress_end
                
                # Chamada recursiva para listar arquivos na subpasta
                sub_arquivos = listar_todos_os_arquivos(
                    token, drive_id, nova_pasta, 
                    progress_bar, sub_start, sub_end,
                    nivel_atual + 1, limite, filtrar_extensoes
                )
                
                arquivos.extend(sub_arquivos)
                
                # Verifica novamente o limite após adicionar os arquivos da subpasta
                if limite and len(arquivos) >= limite:
                    break
            else:
                # Se for um arquivo, adiciona à lista se passar pelo filtro
                nome_arquivo = item.get("name", "").lower()
                
                # Aplica filtro de extensão se fornecido
                if filtrar_extensoes:
                    if any(nome_arquivo.endswith(ext.lower()) for ext in filtrar_extensoes):
                        arquivos.append(item)
                else:
                    arquivos.append(item)
        
        # Verifica se há mais páginas (paginação)
        next_link = response.json().get("@odata.nextLink")
        while next_link and (not limite or len(arquivos) < limite):
            response = requests.get(next_link, headers=headers, timeout=30)
            response.raise_for_status()
            
            itens = response.json().get("value", [])
            for item in itens:
                if not item.get("folder"):
                    nome_arquivo = item.get("name", "").lower()
                    
                    # Aplica filtro de extensão se fornecido
                    if filtrar_extensoes:
                        if any(nome_arquivo.endswith(ext.lower()) for ext in filtrar_extensoes):
                            arquivos.append(item)
                    else:
                        arquivos.append(item)
                
                # Verifica o limite
                if limite and len(arquivos) >= limite:
                    break
            
            # Obtém o próximo link para paginação
            next_link = response.json().get("@odata.nextLink")
        
        # Finaliza a barra de progresso
        if progress_bar and nivel_atual == 0:
            progress_bar.progress(
                progress_end,
                text=f"Busca concluída! Encontrados {len(arquivos)} arquivos."
            )
            time.sleep(0.5)  # Breve pausa para mostrar a mensagem
    
    except requests.exceptions.RequestException as e:
        if nivel_atual == 0:  # Exibe erros apenas no nível principal
            st.warning(f"Erro ao listar arquivos em {caminho_pasta}: {str(e)}")
    
    return arquivos

def baixar_arquivo(
    token: str, 
    download_url: str, 
    nome_arquivo: str, 
    pasta_destino: str = "data"
) -> Tuple[Optional[str], Optional[bytes]]:
    """
    Baixa um único arquivo do SharePoint.
    
    Args:
        token: Token de autenticação
        download_url: URL para download do arquivo
        nome_arquivo: Nome do arquivo para salvar
        pasta_destino: Pasta local para salvar o arquivo
        
    Returns:
        Tupla contendo (caminho_local, conteúdo_binário)
    """
    headers = {"Authorization": f"Bearer {token}"}
    
    # Cria a pasta de destino se não existir
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino)
    
    # Constrói o caminho local para o arquivo
    nome_seguro = nome_arquivo.replace(':', '_').replace('/', '_')
    caminho_local = os.path.join(pasta_destino, nome_seguro)
    
    try:
        # Tenta baixar o arquivo
        response = requests.get(download_url, headers=headers, timeout=60)
        response.raise_for_status()
        conteudo = response.content
        
        # Salva o arquivo localmente
        with open(caminho_local, "wb") as f:
            f.write(conteudo)
        
        return caminho_local, conteudo
    
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro ao baixar {nome_arquivo}: {str(e)}")
        return None, None

def baixar_arquivos(
    token: str,
    arquivos: List[Dict[str, Any]],
    pasta: str = "data",
    extensoes_validas: Optional[List[str]] = None,
    progress_bar: Optional[Any] = None,
    max_tentativas: int = 3
) -> List[str]:
    """
    Baixa múltiplos arquivos do SharePoint.
    
    Args:
        token: Token de autenticação
        arquivos: Lista de dicionários com informações dos arquivos
        pasta: Pasta local para salvar os arquivos
        extensoes_validas: Lista de extensões de arquivo para filtrar
        progress_bar: Objeto de barra de progresso do Streamlit
        max_tentativas: Número máximo de tentativas para cada arquivo
        
    Returns:
        Lista de caminhos para os arquivos baixados
    """
    # Define extensões padrão se não fornecidas
    if extensoes_validas is None:
        extensoes_validas = [
            ".pdf", ".docx", ".pptx", ".xlsx", 
            ".png", ".jpg", ".jpeg", ".gif", ".bmp",
            ".txt", ".csv", ".html"
        ]
    
    # Garante que as extensões estejam em minúsculas
    extensoes_validas = [ext.lower() for ext in extensoes_validas]
    
    # Cria a pasta de destino se não existir
    if not os.path.exists(pasta):
        os.makedirs(pasta)
    
    # Filtra arquivos por extensão
    arquivos_para_baixar = []
    for arq in arquivos:
        nome = arq.get("name", "").lower()
        if any(nome.endswith(ext) for ext in extensoes_validas):
            arquivos_para_baixar.append(arq)
    
    total_arquivos = len(arquivos_para_baixar)
    if total_arquivos == 0:
        st.warning("⚠️ Nenhum arquivo com extensão suportada encontrado para download.")
        return []
    
    # Inicializa progresso
    if progress_bar:
        progress_bar.progress(0, text=f"Preparando para baixar {total_arquivos} arquivos...")
    
    # Lista para armazenar caminhos dos arquivos baixados
    caminhos = []
    
    # Download dos arquivos
    for i, arq in enumerate(arquivos_para_baixar):
        nome = arq.get("name", "")
        link = arq.get("@microsoft.graph.downloadUrl")
        
        if link:
            # Atualiza progresso
            if progress_bar:
                progress_bar.progress(
                    min(i / total_arquivos, 0.99),
                    text=f"Baixando {i+1}/{total_arquivos}: {nome}"
                )
            
            # Tenta baixar com múltiplas tentativas
            for tentativa in range(max_tentativas):
                try:
                    caminho_local, _ = baixar_arquivo(token, link, nome, pasta)
                    if caminho_local:
                        caminhos.append(caminho_local)
                        break
                    elif tentativa < max_tentativas - 1:
                        # Espera antes de tentar novamente
                        time.sleep(2)
                except Exception as e:
                    st.warning(f"Erro ao baixar {nome} (tentativa {tentativa+1}): {e}")
                    if tentativa < max_tentativas - 1:
                        time.sleep(2)
    
    # Finaliza progresso
    if progress_bar:
        progress_bar.progress(
            1.0, 
            text=f"✅ Download concluído! {len(caminhos)}/{total_arquivos} arquivos baixados."
        )
        time.sleep(0.5)
    
    return caminhos

def obter_detalhes_biblioteca(token: str, drive_id: str) -> Dict[str, Any]:
    """
    Obtém detalhes adicionais sobre uma biblioteca específica.
    
    Args:
        token: Token de autenticação
        drive_id: ID da biblioteca
        
    Returns:
        Dicionário com detalhes da biblioteca
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/drives/{drive_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro ao obter detalhes da biblioteca: {str(e)}")
        return {}

def verificar_token(token: str) -> bool:
    """
    Verifica se o token é válido fazendo uma chamada simples.
    
    Args:
        token: Token de autenticação
        
    Returns:
        True se o token for válido, False caso contrário
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_ROOT}/me"  # Uma chamada simples para verificar o token
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except:
        return False
