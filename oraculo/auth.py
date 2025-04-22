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
        client_id = st.
