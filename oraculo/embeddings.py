"""
Módulo de geração de embeddings para processamento de linguagem natural.
Permite criar representações vetoriais de textos para consultas semânticas.
"""

import os
import json
import numpy as np
import streamlit as st
from typing import List, Dict, Any, Union, Optional
from openai import OpenAI

# Dimensões do modelo de embeddings da OpenAI
EMBEDDING_DIMENSIONS = 1536  # para o modelo text-embedding-ada-002

class EmbeddingsManager:
    """Gerencia a criação, armazenamento e consulta de embeddings de texto."""
    
    def __init__(
        self, 
        model: str = "text-embedding-ada-002",
        cache_dir: str = "embeddings_cache",
        use_cache: bool = True
    ):
        """
        Inicializa o gerenciador de embeddings.
        
        Args:
            model: Modelo de embeddings da OpenAI a ser utilizado
            cache_dir: Diretório para armazenar cache de embeddings
            use_cache: Se deve usar cache para evitar chamadas repetidas à API
        """
        self.model = model
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        
        # Cria o diretório de cache se não existir
        if use_cache and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # Inicializa o cliente da OpenAI
        try:
            self.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        except:
            st.warning("API Key da OpenAI não configurada. Embeddings não estarão disponíveis.")
            self.client = None
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """
        Cria um embedding para um texto usando a API da OpenAI.
        
        Args:
            text: Texto para gerar o embedding
            
        Returns:
            Lista de floats representando o embedding ou None em caso de erro
        """
        if not self.client:
            return None
            
        if not text or text.isspace():
            return np.zeros(EMBEDDING_DIMENSIONS).tolist()
            
        # Verifica cache
        if self.use_cache:
            cache_file = self._get_cache_filename(text)
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except:
                    pass  # Se falhar, continua para gerar novo embedding
        
        # Gera embedding via API
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            
            # Salva no cache
            if self.use_cache:
                cache_file = self._get_cache_filename(text)
                with open(cache_file, 'w') as f:
                    json.dump(embedding, f)
                    
            return embedding
            
        except Exception as e:
            st.error(f"Erro ao gerar embedding: {str(e)}")
            return None
    
    def create_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Cria embeddings para uma lista de textos.
        
        Args:
            texts: Lista de textos para gerar embeddings
            
        Returns:
            Lista de embeddings para cada texto
        """
        return [self.create_embedding(text) for text in texts]
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcula a similaridade de cosseno entre dois embeddings.
        
        Args:
            embedding1: Primeiro embedding
            embedding2: Segundo embedding
            
        Returns:
            Valor de similaridade de cosseno (entre 0 e 1)
        """
        if not embedding1 or not embedding2:
            return 0.0
            
        # Converte para arrays numpy
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Normaliza os vetores
        vec1_norm = np.linalg.norm(vec1)
        vec2_norm = np.linalg.norm(vec2)
        
        if vec1_norm == 0 or vec2_norm == 0:
            return 0.0
            
        # Calcula similaridade de cosseno
        cosine_similarity = np.dot(vec1, vec2) / (vec1_norm * vec2_norm)
        
        # Garante que o valor esteja entre 0 e 1
        return float(max(0.0, min(1.0, cosine_similarity)))
    
    def find_most_similar(
        self, 
        query_embedding: List[float], 
        candidate_embeddings: List[List[float]],
        texts: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Union[List[int], List[Dict[str, Any]]]:
        """
        Encontra os textos mais similares a uma consulta.
        
        Args:
            query_embedding: Embedding da consulta
            candidate_embeddings: Lista de embeddings dos textos candidatos
            texts: Lista de textos correspondentes aos embeddings
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de índices ou dicionários com textos mais similares
        """
        if not query_embedding or not candidate_embeddings:
            return []
            
        # Calcula similaridades
        similarities = [
            self.similarity(query_embedding, candidate) 
            for candidate in candidate_embeddings
            if candidate is not None
        ]
        
        # Encontra os índices dos top_k mais similares
        if not similarities:
            return []
            
        top_indices = np.argsort(similarities)[::-1][:top_k].tolist()
        
        # Se os textos foram fornecidos, retorna dicionários com texto e similaridade
        if texts:
            return [
                {
                    "index": idx,
                    "text": texts[idx],
                    "similarity": similarities[idx]
                }
                for idx in top_indices
            ]
        else:
            return top_indices
    
    def search_by_text(
        self, 
        query: str, 
        texts: List[str],
        cached_embeddings: Optional[List[List[float]]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca textos semanticamente similares a uma consulta.
        
        Args:
            query: Texto da consulta
            texts: Lista de textos para buscar
            cached_embeddings: Embeddings pré-calculados (opcional)
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de dicionários com textos mais similares
        """
        # Gera embedding da consulta
        query_embedding = self.create_embedding(query)
        if not query_embedding:
            return []
            
        # Gera embeddings dos textos se não fornecidos
        if cached_embeddings is None:
            candidate_embeddings = self.create_embeddings_batch(texts)
        else:
            candidate_embeddings = cached_embeddings
            
        # Encontra os mais similares
        return self.find_most_similar(query_embedding, candidate_embeddings, texts, top_k)
    
    def _get_cache_filename(self, text: str) -> str:
        """
        Gera um nome de arquivo para cache baseado no hash do texto.
        
        Args:
            text: Texto para gerar o nome do arquivo
            
        Returns:
            Caminho para o arquivo de cache
        """
        import hashlib
        # Gera um hash do texto para usar como nome de arquivo
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.json")
