"""
Módulo de autenticação para a Microsoft Graph API.
Gerencia tokens de acesso e autenticação OAuth para acessar o SharePoint.
"""

import requests
import time
import streamlit as st
from typing import Dict, Optional, Any, Tuple

@st.cache_resource(ttl=3500)  # Quase 1 hora, pois tokens geralmente expiram em 1h
def get_graph_token() -> Optional[str]:
    """
    Obtém um token de autenticação para a Microsoft Graph API usando
    credenciais de aplicativo (client credentials flow).
    
    Returns:
        Token de autenticação ou None em caso de erro
    """
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

def verificar_token_valido(token: str) -> bool:
    """
    Verifica se um token ainda é válido fazendo uma chamada de teste à API.
    
    Args:
        token: Token de autenticação a ser verificado
        
    Returns:
        True se o token ainda é válido, False caso contrário
    """
    if not token:
        return False
        
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://graph.microsoft.com/v1.0/me"  # Endpoint simples para verificação
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code not in (401, 403)  # 401/403 indicam token inválido
    except Exception:
        return False

def get_token_info(token: str) -> Dict[str, Any]:
    """
    Decodifica informações básicas do token JWT.
    Não valida a assinatura, apenas extrai dados do payload.
    
    Args:
        token: Token JWT a ser decodificado
        
    Returns:
        Dicionário com informações do token ou dicionário vazio em caso de erro
    """
    if not token:
        return {}
        
    try:
        # JWT tem formato: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {}
            
        # Decodifica a parte do payload (índice 1)
        import base64
        import json
        
        # Ajusta o padding se necessário
        payload = parts[1]
        payload += '=' * ((4 - len(payload) % 4) % 4)
        
        # Decodifica o payload
        decoded = base64.b64decode(payload)
        info = json.loads(decoded)
        
        # Extrai informações relevantes
        result = {
            "app_id": info.get("appid", ""),
            "tenant_id": info.get("tid", ""),
            "expires": info.get("exp", 0),
            "scopes": info.get("scp", "").split()
        }
        
        # Calcula tempo de expiração em formato legível
        if result["expires"]:
            current_time = int(time.time())
            expires_in = result["expires"] - current_time
            result["expires_in_minutes"] = max(0, int(expires_in / 60))
            
        return result
        
    except Exception as e:
        st.warning(f"Erro ao decodificar token: {str(e)}")
        return {}
