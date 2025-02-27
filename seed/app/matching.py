"""
Système de Mise en Correspondance Candidats-Emplois de Niveau Entreprise
=============================================
Un système haute performance, conforme au RGPD, tolérant aux pannes pour mettre en correspondance les candidats et les emplois.

Fonctionnalités clés:
- Correspondance sémantique avancée utilisant des techniques d'IA hybrides
- Mise en cache vectorielle avec intégration Redis
- Traitement distribué pour un débit élevé
- Sécurité complète et conformité RGPD
- Gestion robuste des erreurs et tolérance aux pannes
- Couverture complète des tests
- Surveillance et observabilité avancées
"""

import warnings
import re
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional, Set, Union, Protocol, TypeVar, Callable
from dataclasses import dataclass, field, asdict
import abc
import inspect
import hashlib
import time
import heapq
import asyncio
import logging
import traceback
import signal
import uuid
import json
import string
import pickle
import os
import yaml
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import lru_cache, wraps, partial
from contextlib import contextmanager, asynccontextmanager

# Clients API
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import ChatCompletion, Choice

# Framework web
from flask import Flask, jsonify, request, send_file, Response, abort, g, Blueprint
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from pydantic import BaseModel, validator, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from waitress import serve

# Configuration et environnement
from dotenv import load_dotenv
from retry import retry
from tenacity import retry as tenacity_retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Base de données
import redis
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool

# Définitions de types
T = TypeVar('T')
U = TypeVar('U')
Result = TypeVar('Result')
Error = TypeVar('Error')

# ============= 1. ARCHITECTURE DU SYSTÈME =============

class AppConfig:
    """Configuration de l'application avec prise en charge des variables d'environnement."""
    
    def __init__(self, env_file: str = ".env"):
        # Chargement des variables d'environnement
        load_dotenv(env_file)
        
        # Paramètres de base
        self.app_name = os.getenv("APP_NAME", "MatchingSystem")
        self.app_version = os.getenv("APP_VERSION", "2.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Clés API
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_org_id = os.getenv("OPENAI_ORG_ID")
        
        # Base de données
        self.database_url = os.getenv("DATABASE_URL")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Paramètres API
        self.model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.api_rate_limit = int(os.getenv("API_RATE_LIMIT", "10"))
        self.enable_batch_processing = os.getenv("ENABLE_BATCH_PROCESSING", "true").lower() == "true"
        self.batch_size = int(os.getenv("BATCH_SIZE", "10"))
        
        # Paramètres de cache
        self.cache_ttl = int(os.getenv("CACHE_TTL", "86400"))  # 24 heures
        self.enable_redis_cache = os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"
        self.cache_dir = os.getenv("CACHE_DIR", os.path.join(os.getcwd(), "cache"))
        
        # Performance
        self.worker_threads = int(os.getenv("WORKER_THREADS", "4"))
        self.timeout = int(os.getenv("TIMEOUT", "30"))
        
        # Sécurité
        self.enable_api_key_auth = os.getenv("ENABLE_API_KEY_AUTH", "false").lower() == "true"
        self.api_key = os.getenv("API_KEY")
        self.anonymize_data = os.getenv("ANONYMIZE_DATA", "true").lower() == "true"
        
        # Pondérations pour le scoring
        self.scoring_weights = {
            'hard_skills': float(os.getenv("WEIGHT_HARD_SKILLS", "0.40")),
            'soft_skills': float(os.getenv("WEIGHT_SOFT_SKILLS", "0.10")),
            'experience': float(os.getenv("WEIGHT_EXPERIENCE", "0.20")),
            'degree': float(os.getenv("WEIGHT_DEGREE", "0.15")),
            'salary': float(os.getenv("WEIGHT_SALARY", "0.025")),
            'remote_work': float(os.getenv("WEIGHT_REMOTE_WORK", "0.025")),
            'languages': float(os.getenv("WEIGHT_LANGUAGES", "0.10")),
        }
        
        # Chemins d'entrée/sortie
        self.output_dir = os.getenv("OUTPUT_DIR", os.path.join(os.getcwd(), "outputs"))
        
        # Création des répertoires requis
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir la configuration en dictionnaire."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def validate(self) -> List[str]:
        """Valider la configuration et renvoyer une liste d'erreurs."""
        errors = []
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY est requis")
            
        if self.enable_api_key_auth and not self.api_key:
            errors.append("API_KEY est requis lorsque ENABLE_API_KEY_AUTH est vrai")
            
        if self.enable_redis_cache and not self.redis_url:
            errors.append("REDIS_URL est requis lorsque ENABLE_REDIS_CACHE est vrai")
            
        return errors

# Initialisation de la configuration
config = AppConfig()

# Configuration de la journalisation
log_level = logging.DEBUG if config.debug else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{config.app_name.lower()}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(config.app_name)

# Validation de la configuration
config_errors = config.validate()
if config_errors:
    for error in config_errors:
        logger.error(f"Erreur de configuration: {error}")
    raise ValueError(f"Configuration invalide: {', '.join(config_errors)}")

# ============= 2. MODÈLES DE DOMAINE =============

class BaseDataModel(BaseModel):
    """Modèle de base avec fonctionnalités communes."""
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

@dataclass
class Experience:
    """Représente une expérience professionnelle."""
    name: str
    months: int
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire."""
        return asdict(self)

@dataclass
class Candidate:
    """Représente un candidat à un emploi."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    experiences: List[Dict[str, Any]] = field(default_factory=list)
    hard_skills: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)
    degree_label: Optional[str] = None
    degree_level: Optional[str] = None
    languages: Dict[str, str] = field(default_factory=dict)
    min_salary: Optional[float] = None
    wants_remote: bool = False
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire."""
        return asdict(self)
    
    def anonymize(self) -> 'Candidate':
        """Créer une version anonymisée pour la conformité RGPD."""
        result = Candidate(
            id=self.id,
            experiences=self.experiences,
            hard_skills=self.hard_skills,
            soft_skills=self.soft_skills,
            degree_label=self.degree_label,
            degree_level=self.degree_level,
            languages=self.languages,
            min_salary=self.min_salary,
            wants_remote=self.wants_remote,
            tags=self.tags
        )
        
        if self.name:
            result.name = f"Candidate_{hashlib.md5(self.name.encode()).hexdigest()[:8]}"
        
        return result

@dataclass
class RequiredExperience:
    """Représente une expérience requise pour un emploi."""
    name: str
    months: int
    category: str = "recommandée"  # 'obligatoire' ou 'recommandée'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire."""
        return asdict(self)

@dataclass
class RequiredSkill:
    """Représente une compétence requise pour un emploi."""
    skill: str
    category: str = "recommandé"  # 'obligatoire' ou 'recommandé'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire."""
        return asdict(self)

@dataclass
class Job:
    """Représente une offre d'emploi."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    required_experiences: List[Dict[str, Any]] = field(default_factory=list)
    required_degree: Optional[str] = None
    salary: Optional[float] = None
    offers_remote: bool = False
    hard_skills: List[Dict[str, str]] = field(default_factory=list)
    required_soft_skills: List[str] = field(default_factory=list)
    required_languages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire."""
        return asdict(self)

@dataclass
class MatchResult:
    """Représente le résultat de la mise en correspondance d'un candidat avec un emploi."""
    candidate_id: str
    job_id: str
    total_score: float
    component_scores: Dict[str, float]
    detailed_scores: Dict[str, Any]
    computation_time: float
    api_calls: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire."""
        return asdict(self)

# ============= 3. COUCHE D'ACCÈS AUX DONNÉES =============

class CacheStrategy(abc.ABC):
    """Classe de base abstraite pour les stratégies de cache."""
    
    @abc.abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Récupérer une valeur du cache."""
        pass
    
    @abc.abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Définir une valeur dans le cache."""
        pass
    
    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        """Supprimer une valeur du cache."""
        pass
    
    @abc.abstractmethod
    async def flush(self) -> None:
        """Vider le cache."""
        pass
    
    @abc.abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du cache."""
        pass

class FileSystemCache(CacheStrategy):
    """Implémentation du cache basée sur le système de fichiers."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.hits = 0
        self.misses = 0
        self.caches = {}
        self.load_all_caches()
    
    def load_all_caches(self) -> None:
        """Charger tous les fichiers de cache en mémoire."""
        cache_files = {
            'similarity': os.path.join(self.cache_dir, 'similarity_cache.pkl'),
            'embeddings': os.path.join(self.cache_dir, 'embeddings_cache.pkl'),
            'hard_skills': os.path.join(self.cache_dir, 'hard_skills_cache.pkl'),
            'soft_skills': os.path.join(self.cache_dir, 'soft_skills_cache.pkl'),
            'degree': os.path.join(self.cache_dir, 'degree_cache.pkl'),
        }
        
        for cache_type, file_path in cache_files.items():
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        self.caches[cache_type] = pickle.load(f)
                else:
                    self.caches[cache_type] = {}
                logger.info(f"Chargé {len(self.caches[cache_type])} éléments depuis {file_path}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du cache {file_path}: {e}")
                self.caches[cache_type] = {}
    
    def save_cache(self, cache_type: str) -> None:
        """Sauvegarder un cache spécifique sur le disque."""
        file_path = os.path.join(self.cache_dir, f'{cache_type}_cache.pkl')
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(self.caches.get(cache_type, {}), f)
            logger.info(f"Enregistré {len(self.caches.get(cache_type, {}))} éléments dans {file_path}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du cache {file_path}: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Récupérer une valeur du cache."""
        cache_type, _, item_key = key.partition(':')
        
        if cache_type not in self.caches:
            self.caches[cache_type] = {}
            self.misses += 1
            return None
        
        if item_key in self.caches[cache_type]:
            self.hits += 1
            return self.caches[cache_type][item_key]
        
        self.misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Définir une valeur dans le cache."""
        cache_type, _, item_key = key.partition(':')
        
        if cache_type not in self.caches:
            self.caches[cache_type] = {}
        
        self.caches[cache_type][item_key] = value
        
        # Sauvegarder sur disque périodiquement
        if len(self.caches[cache_type]) % 50 == 0:
            self.save_cache(cache_type)
    
    async def delete(self, key: str) -> None:
        """Supprimer une valeur du cache."""
        cache_type, _, item_key = key.partition(':')
        
        if cache_type in self.caches and item_key in self.caches[cache_type]:
            del self.caches[cache_type][item_key]
    
    async def flush(self) -> None:
        """Vider tous les caches."""
        for cache_type in self.caches:
            self.caches[cache_type] = {}
            self.save_cache(cache_type)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du cache."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": {k: len(v) for k, v in self.caches.items()},
            "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }

class RedisCache(CacheStrategy):
    """Implémentation du cache basée sur Redis."""
    
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
        self.hits = 0
        self.misses = 0
        self.prefix = "matching:"
    
    async def get(self, key: str) -> Optional[Any]:
        """Récupérer une valeur du cache."""
        full_key = f"{self.prefix}{key}"
        try:
            value = self.redis_client.get(full_key)
            if value:
                self.hits += 1
                return pickle.loads(value)
            self.misses += 1
            return None
        except Exception as e:
            logger.error(f"Erreur Redis get: {e}")
            self.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Définir une valeur dans le cache."""
        full_key = f"{self.prefix}{key}"
        try:
            serialized = pickle.dumps(value)
            if ttl:
                self.redis_client.setex(full_key, ttl, serialized)
            else:
                self.redis_client.set(full_key, serialized)
        except Exception as e:
            logger.error(f"Erreur Redis set: {e}")
    
    async def delete(self, key: str) -> None:
        """Supprimer une valeur du cache."""
        full_key = f"{self.prefix}{key}"
        try:
            self.redis_client.delete(full_key)
        except Exception as e:
            logger.error(f"Erreur Redis delete: {e}")
    
    async def flush(self) -> None:
        """Vider toutes les clés avec préfixe."""
        try:
            # Obtenir toutes les clés avec ce préfixe
            pattern = f"{self.prefix}*"
            keys = self.redis_client.keys(pattern)
            
            # Les supprimer par lots
            if keys:
                for i in range(0, len(keys), 1000):
                    self.redis_client.delete(*keys[i:i+1000])
        except Exception as e:
            logger.error(f"Erreur Redis flush: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du cache."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
            "info": {k.decode('utf8'): v.decode('utf8') for k, v in self.redis_client.info().items()}
        }

class CacheService:
    """Service pour la mise en cache d'opérations coûteuses."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Initialiser la stratégie de cache
        if config.enable_redis_cache:
            self.cache = RedisCache(config.redis_url)
            logger.info("Utilisation du cache Redis")
        else:
            self.cache = FileSystemCache(config.cache_dir)
            logger.info("Utilisation du cache système de fichiers")
        
        # Statistiques
        self.api_calls = 0
    
    def get_similarity_key(self, text1: str, text2: str) -> str:
        """Générer une clé de cache cohérente pour deux éléments textuels."""
        # Normaliser et trier les textes pour des clés cohérentes
        texts = sorted([normalize_text(text1), normalize_text(text2)])
        key_hash = hashlib.md5('|'.join(texts).encode()).hexdigest()
        return f"similarity:{key_hash}"
    
    def get_embedding_key(self, text: str) -> str:
        """Générer une clé de cache pour un embedding."""
        normalized = normalize_text(text)
        key_hash = hashlib.md5(normalized.encode()).hexdigest()
        return f"embeddings:{key_hash}"
    
    async def get_similarity(self, cache_type: str, text1: str, text2: str) -> Optional[float]:
        """Obtenir le score de similarité depuis le cache."""
        key = self.get_similarity_key(text1, text2)
        return await self.cache.get(f"{cache_type}:{key}")
    
    async def set_similarity(self, cache_type: str, text1: str, text2: str, score: float) -> None:
        """Définir le score de similarité dans le cache."""
        key = self.get_similarity_key(text1, text2)
        await self.cache.set(f"{cache_type}:{key}", score, self.config.cache_ttl)
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Obtenir l'embedding depuis le cache."""
        key = self.get_embedding_key(text)
        return await self.cache.get(f"embeddings:{key}")
    
    async def set_embedding(self, text: str, embedding: List[float]) -> None:
        """Définir l'embedding dans le cache."""
        key = self.get_embedding_key(text)
        await self.cache.set(f"embeddings:{key}", embedding, self.config.cache_ttl)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du cache."""
        cache_stats = await self.cache.get_stats()
        return {
            "api_calls": self.api_calls,
            "cache": cache_stats
        }

# ============= 4. COUCHE DE SERVICE =============

class OpenAIService:
    """Service pour interagir avec l'API OpenAI."""
    
    def __init__(self, config: AppConfig, cache_service: CacheService):
        self.config = config
        self.cache_service = cache_service
        
        # Initialiser les clients
        self.client = OpenAI(api_key=config.openai_api_key, organization=config.openai_org_id)
        self.async_client = AsyncOpenAI(api_key=config.openai_api_key, organization=config.openai_org_id)
        
        # Statistiques
        self.total_tokens = 0
    
    @tenacity_retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception)
    )
    async def get_completion(
        self, 
        prompt: str, 
        temperature: float = 0,
        max_tokens: int = 1000,
        json_response: bool = False
    ) -> str:
        """Obtenir une complétion de l'API OpenAI avec logique de réessai."""
        try:
            self.cache_service.api_calls += 1
            
            # Construire les messages
            messages = [{"role": "user", "content": prompt}]
            
            # Format de réponse optionnel pour JSON
            response_format = {"type": "json_object"} if json_response else None
            
            # Faire l'appel API
            response = await self.async_client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            
            # Mettre à jour l'utilisation des tokens
            self.total_tokens += response.usage.total_tokens
            
            # Renvoyer le contenu
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"Erreur API OpenAI: {e}")
            raise
    
    @tenacity_retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception)
    )
    async def get_embeddings(self, texts: List[str]) -> Dict[str, List[float]]:
        """Obtenir des embeddings pour un lot de textes."""
        result = {}
        uncached_texts = []
        
        # Vérifier d'abord le cache
        for text in texts:
            normalized = normalize_text(text)
            embedding = await self.cache_service.get_embedding(normalized)
            
            if embedding is not None:
                result[normalized] = embedding
            else:
                uncached_texts.append(normalized)
        
        # S'il y a des textes non mis en cache, les récupérer
        if uncached_texts:
            try:
                self.cache_service.api_calls += 1
                
                # Faire l'appel API
                response = await self.async_client.embeddings.create(
                    model=self.config.embedding_model,
                    input=uncached_texts
                )
                
                # Traiter les résultats
                for i, embedding_data in enumerate(response.data):
                    text = uncached_texts[i]
                    embedding = embedding_data.embedding
                    
                    # Stocker à la fois dans le résultat et le cache
                    result[text] = embedding
                    await self.cache_service.set_embedding(text, embedding)
            
            except Exception as e:
                logger.error(f"Erreur lors de l'obtention des embeddings: {e}")
                # Renvoyer des embeddings vides pour les textes échoués
                for text in uncached_texts:
                    result[text] = []
        
        return result
    
    async def batch_similarity_with_gpt(
        self,
        items1: List[str],
        items2: List[str],
        context: str,
        cache_type: str
    ) -> Dict[Tuple[str, str], float]:
        """
        Traiter les comparaisons de similarité par lots à l'aide de GPT pour réduire les appels API.
        """
        results = {}
        comparisons_needed = []
        
        # Vérifier d'abord le cache
        for item1 in items1:
            for item2 in items2:
                similarity = await self.cache_service.get_similarity(cache_type, item1, item2)
                
                if similarity is not None:
                    results[(item1, item2)] = similarity
                else:
                    comparisons_needed.append((item1, item2))
        
        # Si nous avons des comparaisons non mises en cache, les traiter par lots
        if comparisons_needed:
            batch_size = min(self.config.batch_size, len(comparisons_needed))
            batches = [comparisons_needed[i:i + batch_size] for i in range(0, len(comparisons_needed), batch_size)]
            
            for batch in batches:
                # Créer un prompt avec une table de comparaison pour le lot
                table = "| Élément 1 | Élément 2 |\n|-------|-------|\n"
                for item1, item2 in batch:
                    table += f"| {item1} | {item2} |\n"
                
                prompt = (
                    f"{context}\n\n"
                    "Veuillez analyser chaque paire dans le tableau suivant et fournir un score de similarité de 0.0 à 1.0 pour chacune :\n\n"
                    f"{table}\n\n"
                    "Répondez UNIQUEMENT avec un tableau JSON valide d'objets, où chaque objet contient :\n"
                    "- 'item1': le premier élément\n"
                    "- 'item2': le deuxième élément\n"
                    "- 'score': le score de similarité (0.0-1.0)\n\n"
                    "Format de réponse exemple :\n"
                    "[{\"item1\":\"Python\",\"item2\":\"Java\",\"score\":0.7}, ...]\n"
                )
                
                try:
                    # Obtenir la complétion
                    content = await self.get_completion(prompt, json_response=True)
                    
                    # Analyser la réponse JSON
                    try:
                        data = json.loads(content)
                        comparisons = data
                        
                        # Gérer les structures imbriquées
                        if isinstance(data, dict) and 'comparisons' in data:
                            comparisons = data['comparisons']
                        
                        # Traiter chaque comparaison
                        for comp in comparisons:
                            if isinstance(comp, dict) and 'item1' in comp and 'item2' in comp and 'score' in comp:
                                item1 = comp['item1']
                                item2 = comp['item2']
                                score = float(comp['score'])
                                
                                # S'assurer que le score est entre 0 et 1
                                score = max(0.0, min(1.0, score))
                                
                                # Stocker le résultat et mettre à jour le cache
                                results[(item1, item2)] = score
                                await self.cache_service.set_similarity(cache_type, item1, item2, score)
                    
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.error(f"Erreur lors de l'analyse de la réponse GPT: {e}")
                        logger.error(f"Contenu de la réponse: {content}")
                        
                        # Repli sur les embeddings pour ce lot
                        await self._fallback_to_embeddings(batch, results, cache_type)
                
                except Exception as e:
                    logger.error(f"Erreur dans la comparaison GPT par lots: {e}")
                    
                    # Repli sur les embeddings pour ce lot
                    await self._fallback_to_embeddings(batch, results, cache_type)
        
        return results
    
    async def _fallback_to_embeddings(
        self,
        batch: List[Tuple[str, str]],
        results: Dict[Tuple[str, str], float],
        cache_type: str
    ) -> None:
        """Repli sur la similarité basée sur les embeddings lorsque GPT échoue."""
        # Obtenir tous les textes uniques
        all_texts = list(set(item for pair in batch for item in pair))
        
        # Obtenir les embeddings pour tous les textes
        embeddings = await self.get_embeddings(all_texts)
        
        # Calculer les similarités
        for item1, item2 in batch:
            vec1 = embeddings.get(normalize_text(item1), [])
            vec2 = embeddings.get(normalize_text(item2), [])
            
            # Calculer la similarité cosinus
            similarity = self._cosine_similarity(vec1, vec2)
            
            # Stocker le résultat et mettre à jour le cache
            results[(item1, item2)] = similarity
            await self.cache_service.set_similarity(cache_type, item1, item2, similarity)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculer la similarité cosinus entre deux vecteurs."""
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du service."""
        return {
            "total_tokens": self.total_tokens,
            "api_calls": self.cache_service.api_calls
        }

class MatchingService:
    """Service pour mettre en correspondance les candidats avec les emplois."""
    
    def __init__(self, config: AppConfig, openai_service: OpenAIService, cache_service: CacheService):
        self.config = config
        self.openai_service = openai_service
        self.cache_service = cache_service
        
        # Constantes
        self.LANGUAGE_LEVELS = {
            "rien": 0,
            "débutant": 1,
            "intermédiaire": 2,
            "courant": 3,
            "bilingue/maternelle": 4
        }
        
        self.DEGREE_LEVELS = {
            "Bac": 0.5,
            "Bac. Pro.": 0.5,
            "BEP / CAP": 0.5,
            "Licence 1": 1,
            "Licence 2": 2,
            "Licence 3": 3,
            "Master 1": 4,
            "Mastère 1": 4,
            "Master 2": 5,
            "Mastère 2": 5,
        }
    
    async def compare_hard_skills(
        self,
        candidate_skills: List[str],
        job_skills: List[Dict[str, str]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Comparer les compétences techniques du candidat avec celles du poste en utilisant un traitement par lots.
        """
        if not candidate_skills or not job_skills:
            return 0.0, {}
        
        # Extraire les noms des compétences
        job_skill_names = [item["skill"] for item in job_skills]
        
        # Obtenir tous les scores de similarité en un seul lot
        context = (
            "Vous êtes un recruteur technique spécialisé dans les compétences informatiques. "
            "Évaluez la similarité entre les compétences techniques en tenant compte des synonymes, "
            "des technologies connexes et des compétences qui se chevauchent dans l'industrie technologique."
        )
        
        # Traiter les similarités par lots
        similarities = await self.openai_service.batch_similarity_with_gpt(
            candidate_skills,
            job_skill_names,
            context,
            'hard_skills'
        )
        
        # Calculer les meilleures correspondances et les scores
        detailed_scores = {}
        obligatory_scores = []
        recommended_scores = []
        
        for job_skill_info in job_skills:
            job_skill = job_skill_info["skill"]
            category = job_skill_info["category"].lower()
            
            # Trouver la meilleure compétence correspondante du candidat
            best_score = 0.0
            best_candidate_skill = None
            
            for cand_skill in candidate_skills:
                score = similarities.get((cand_skill, job_skill), 0.0)
                if score > best_score:
                    best_score = score
                    best_candidate_skill = cand_skill
            
            # Appliquer la logique spécifique à la catégorie
            if category == "obligatoire" and best_score < 0.8:
                final_score = 0.0
            else:
                final_score = best_score
            
            # Ajouter à la catégorie appropriée
            if category == "obligatoire":
                obligatory_scores.append(final_score)
            else:
                recommended_scores.append(final_score)
            
            # Stocker les informations détaillées sur la correspondance
            detailed_scores[job_skill] = {
                "job_skill": job_skill,
                "candidate_skill": best_candidate_skill,
                "score": final_score,
                "category": category
            }
        
        # Calculer le score final
        if obligatory_scores and recommended_scores:
            final_score = 0.7 * np.mean(obligatory_scores) + 0.3 * np.mean(recommended_scores)
        elif obligatory_scores:
            final_score = np.mean(obligatory_scores)
        elif recommended_scores:
            final_score = np.mean(recommended_scores)
        else:
            final_score = 0.0
        
        return final_score, detailed_scores
    
    async def compare_soft_skills(
        self,
        candidate_skills: List[str],
        job_skills: List[str]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Comparer les compétences comportementales du candidat avec celles du poste en utilisant un traitement par lots.
        """
        if not candidate_skills or not job_skills:
            return 0.0, {}
        
        # Obtenir tous les scores de similarité en un seul lot
        context = (
            "Vous êtes un recruteur spécialisé dans l'évaluation des compétences comportementales. "
            "Évaluez la similarité entre les compétences comportementales en tenant compte de leur signification, "
            "du chevauchement des compétences et de leur application dans des contextes professionnels."
        )
        
        # Traiter les similarités par lots
        similarities = await self.openai_service.batch_similarity_with_gpt(
            candidate_skills,
            job_skills,
            context,
            'soft_skills'
        )
        
        # Trouver la meilleure compétence correspondante du candidat pour chaque compétence du poste
        detailed_scores = {}
        scores = []
        
        for job_skill in job_skills:
            best_score = 0.0
            best_candidate_skill = None
            
            for cand_skill in candidate_skills:
                score = similarities.get((cand_skill, job_skill), 0.0)
                if score > best_score:
                    best_score = score
                    best_candidate_skill = cand_skill
            
            scores.append(best_score)
            detailed_scores[job_skill] = {
                "job_skill": job_skill,
                "candidate_skill": best_candidate_skill,
                "score": best_score
            }
        
        # Calculer le score moyen
        final_score = np.mean(scores) if scores else 0.0
        
        return final_score, detailed_scores
    
    async def compare_experiences(
        self,
        candidate_experiences: List[Dict[str, Any]],
        required_experiences: List[Dict[str, Any]]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Comparer les expériences du candidat avec les expériences requises en utilisant un traitement par lots.
        """
        if not candidate_experiences or not required_experiences:
            return 0.0, []
        
        # Extraire les noms pour la comparaison par lots
        candidate_exp_names = [exp["name"] for exp in candidate_experiences]
        required_exp_names = [exp["name"] for exp in required_experiences]
        
        # Obtenir tous les scores de similarité des noms en un seul lot
        context = (
            "Vous êtes un professionnel RH spécialisé dans le recrutement informatique. "
            "Évaluez la similarité entre les titres de poste en tenant compte de leurs responsabilités, "
            "des compétences requises et du travail typique dans l'industrie technologique."
        )
        
        # Traiter les similarités par lots
        name_similarities = await self.openai_service.batch_similarity_with_gpt(
            candidate_exp_names,
            required_exp_names,
            context,
            'experience'
        )
        
        # Calculer les scores pour toutes les expériences
        experience_details = []
        obligatory_scores = []
        recommended_scores = []
        
        for req_idx, required_exp in enumerate(required_experiences):
            req_name = required_exp["name"]
            req_months = required_exp.get("months", 0)
            category = required_exp.get("category", "").lower()
            
            best_total_score = 0.0
            best_detail = {
                "name_score": 0.0,
                "duration_score": 0.0
            }
            
            # Trouver la meilleure expérience correspondante du candidat
            for cand_idx, cand_exp in enumerate(candidate_experiences):
                cand_name = cand_exp["name"]
                cand_months = cand_exp.get("months", 0)
                
                # Obtenir la similarité des noms à partir des résultats du lot
                name_score = name_similarities.get((cand_name, req_name), 0.0)
                
                # Calculer le score de durée
                duration_score = min(1.0, cand_months / req_months) if req_months > 0 else 1.0
                
                # Calculer le score total avec des pondérations
                total_score = 0.7 * name_score + 0.3 * duration_score
                
                if total_score > best_total_score:
                    best_total_score = total_score
                    best_detail = {
                        "name_score": name_score,
                        "duration_score": duration_score
                    }
            
            # Ajouter le score à la catégorie appropriée
            if category == "obligatoire":
                obligatory_scores.append(best_total_score)
            else:
                recommended_scores.append(best_total_score)
            
            # Stocker les détails
            experience_details.append({
                "required_exp_name": req_name,
                "category": category,
                "best_score": best_total_score,
                "sub_scores": best_detail
            })
        
        # Calculer le score final
        if obligatory_scores and recommended_scores:
            final_score = 0.7 * np.mean(obligatory_scores) + 0.3 * np.mean(recommended_scores)
        elif obligatory_scores:
            final_score = np.mean(obligatory_scores)
        elif recommended_scores:
            final_score = np.mean(recommended_scores)
        else:
            final_score = 0.0
        
        return final_score, experience_details
    
    async def calculate_diploma_score(
        self,
        candidate_label: str,
        candidate_level: str,
        required_degree: str
    ) -> float:
        """
        Calculer le score du diplôme en fonction de la correspondance de niveau et de la similarité de domaine.
        """
        if not candidate_label or not candidate_level or not required_degree:
            return 0.0
        
        # Extraire le niveau du diplôme requis
        required_level = required_degree
        for level in self.DEGREE_LEVELS.keys():
            if level in required_degree:
                required_level = level
                break
        
        # Analyser le domaine du diplôme requis
        required_field = required_degree.replace(required_level, "").strip()
        
        # Obtenir les valeurs numériques pour les niveaux
        candidate_level_value = self.DEGREE_LEVELS.get(candidate_level, 0)
        required_level_value = self.DEGREE_LEVELS.get(required_level, 0)
        
        # Calculer le score de niveau
        if required_level_value > 0:
            level_score = min(1.0, candidate_level_value / required_level_value)
        else:
            level_score = 0.0
        
        # Calculer la similarité de domaine
        if required_field and candidate_label:
            # Préparer les noms de domaine
            candidate_field = self._preprocess_diploma_name(candidate_label)
            required_field = self._preprocess_diploma_name(required_field)
            
            # Obtenir le score de similarité
            similarity = await self.cache_service.get_similarity('degree', candidate_field, required_field)
            
            if similarity is None:
                # Obtenir les embeddings
                embeddings = await self.openai_service.get_embeddings([candidate_field, required_field])
                
                # Calculer la similarité
                vec1 = embeddings.get(normalize_text(candidate_field), [])
                vec2 = embeddings.get(normalize_text(required_field), [])
                
                similarity = self.openai_service._cosine_similarity(vec1, vec2)
                
                # Mettre en cache le résultat
                await self.cache_service.set_similarity('degree', candidate_field, required_field, similarity)
            
            field_score = similarity
        else:
            field_score = 1.0  # Par défaut si aucun domaine à comparer
        
        # Calculer le score final (pondéré)
        final_score = (0.8 * level_score) + (0.2 * field_score)
        return final_score
    
    def _preprocess_diploma_name(self, diploma_name: str) -> str:
        """Prétraiter le nom du diplôme en développant les abréviations."""
        abbreviation_mapping = {
            "IA": "Intelligence Artificielle",
            "AI": "Intelligence Artificielle",
            "Développement Web": "Développement Web",
            "Intelligence Artificielle": "Intelligence Artificielle",
            "Data Science": "Science des Données",
        }
        result = diploma_name
        for abbr, full_term in abbreviation_mapping.items():
            result = result.replace(abbr, full_term)
        return result
    
    def calculate_language_score(
        self,
        candidate_languages: Dict[str, str],
        job_languages: Dict[str, Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculer le score de langue en fonction des langues requises et recommandées.
        """
        if not job_languages:
            return 1.0, {}
        
        required_scores = []
        recommended_scores = []
        detailed_scores = {}
        
        for language, details in job_languages.items():
            job_level = details.get("level", "")
            is_required = details.get("required", False)
            
            # Obtenir le niveau du candidat pour cette langue
            candidate_level = candidate_languages.get(language.lower(), "rien")
            
            # Convertir les niveaux en valeurs numériques
            candidate_level_value = self.LANGUAGE_LEVELS.get(candidate_level.lower(), 0)
            job_level_value = self.LANGUAGE_LEVELS.get(job_level.lower(), 0)
            
            # Calculer le score
            level_diff = candidate_level_value - job_level_value
            
            if is_required:
                if level_diff < 0:
                    score = max(0, 1.0 + (-0.4 - 0.2 * (abs(level_diff) - 1)))
                else:
                    score = 1.0 + 0.05 * level_diff
                required_scores.append(score)
            else:
                if level_diff < 0:
                    score = max(0, 1.0 - 0.2 * abs(level_diff))
                else:
                    score = 1.0 + 0.05 * level_diff
                recommended_scores.append(score)
            
            # Stocker les détails
            detailed_scores[language] = {
                "candidate_level": candidate_level,
                "job_level": job_level,
                "score": score,
                "category": "obligatoire" if is_required else "recommandé"
            }
        
        # Calculer le score final
        if required_scores and recommended_scores:
            total_score = (0.6 * np.mean(required_scores)) + (0.4 * np.mean(recommended_scores))
        elif required_scores:
            total_score = np.mean(required_scores)
        elif recommended_scores:
            total_score = np.mean(recommended_scores)
        else:
            total_score = 0.0
        
        return total_score, detailed_scores
    
    def calculate_misc_scores(
        self,
        candidate: Dict[str, Any],
        job: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculer les scores divers (salaire et travail à distance).
        """
        results = {}
        
        # Score de salaire
        candidate_min_salary = candidate.get("min_salary", 0)
        job_salary = job.get("salary", 0)
        results["salary"] = 1.0 if job_salary >= candidate_min_salary else 0.0
        
        # Score de travail à distance
        candidate_wants_remote = candidate.get("wants_remote", False)
        job_offers_remote = job.get("offers_remote", False)
        results["remote_work"] = 1.0 if candidate_wants_remote == job_offers_remote else 0.0
        
        return results
    
    def adaptive_weights(self, job: Dict[str, Any]) -> Dict[str, float]:
        """Adapter les pondérations en fonction des données d'emploi disponibles."""
        # Commencer avec les pondérations de base
        new_weights = dict(self.config.scoring_weights)
        
        # Identifier les champs manquants
        fields_absent = []
        if not job.get('hard_skills'):
            fields_absent.append('hard_skills')
        if not job.get('required_experiences'):
            fields_absent.append('experience')
        if not job.get('required_degree'):
            fields_absent.append('degree')
        if job.get('salary') is None:
            fields_absent.append('salary')
        if 'offers_remote' not in job:
            fields_absent.append('remote_work')
        if not job.get('required_languages'):
            fields_absent.append('languages')
        if not job.get('required_soft_skills'):
            fields_absent.append('soft_skills')
        
        # Mettre les pondérations à zéro pour les champs manquants
        for field in fields_absent:
            new_weights[field] = 0.0
        
        # Calculer la somme fixe (champs qui ne seront pas redistribués)
        fixed_sum = sum(new_weights[f] for f in {"salary", "remote_work"} if f not in fields_absent)
        
        # Déterminer les champs ajustables et leur somme
        adjustable_fields = [f for f in new_weights if f not in {"salary", "remote_work"} and f not in fields_absent]
        adjustable_sum = sum(new_weights[f] for f in adjustable_fields)
        
        # Redistribuer les pondérations
        sum_all = sum(self.config.scoring_weights.values())
        sum_current = fixed_sum + adjustable_sum
        mass_to_redistribute = sum_all - sum_current
        
        if adjustable_sum > 0:
            ratio = (adjustable_sum + mass_to_redistribute) / adjustable_sum
            for field in adjustable_fields:
                new_weights[field] *= ratio
        
        return new_weights
    
    async def calculate_match_score(
        self,
        candidate: Dict[str, Any],
        job: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculer le score de correspondance entre un candidat et un emploi.
        """
        start_time = time.perf_counter()
        
        # Vérifier d'abord les tags pour un filtrage précoce
        candidate_tags = set(tag.lower() for tag in candidate.get("tags", []))
        job_tags = set(tag.lower() for tag in job.get("tags", []))
        common_tags = candidate_tags.intersection(job_tags)
        
        if not common_tags:
            return {
                "total_score": 0.0,
                "reason": "Aucun tag correspondant",
                "computation_time": time.perf_counter() - start_time
            }
        
        # Calculer le bonus de tag
        num_common_tags = len(common_tags)
        tag_bonus = 0.05 if num_common_tags == 2 else 0.10 if num_common_tags >= 3 else 0.0
        
        # Ajuster les pondérations en fonction des données d'emploi disponibles
        weights = self.adaptive_weights(job)
        
        # Exécuter toutes les tâches de scoring simultanément
        tasks = []
        task_types = []
        
        # Comparaison des compétences techniques
        if job.get("hard_skills") and candidate.get("hard_skills"):
            tasks.append(self.compare_hard_skills(
                candidate.get("hard_skills", []),
                job.get("hard_skills", [])
            ))
            task_types.append("hard_skills")
        
        # Comparaison des compétences comportementales
        if job.get("required_soft_skills") and candidate.get("soft_skills"):
            tasks.append(self.compare_soft_skills(
                candidate.get("soft_skills", []),
                job.get("required_soft_skills", [])
            ))
            task_types.append("soft_skills")
        
        # Comparaison des expériences
        if job.get("required_experiences") and candidate.get("experiences"):
            tasks.append(self.compare_experiences(
                candidate.get("experiences", []),
                job.get("required_experiences", [])
            ))
            task_types.append("experience")
        
        # Score de diplôme
        if job.get("required_degree") and candidate.get("degree_label") and candidate.get("degree_level"):
            tasks.append(self.calculate_diploma_score(
                candidate.get("degree_label", ""),
                candidate.get("degree_level", ""),
                job.get("required_degree", "")
            ))
            task_types.append("degree")
        
        # Exécuter les tâches simultanément
        task_results = await asyncio.gather(*tasks)
        
        # Initialiser les scores des composants
        component_scores = defaultdict(float)
        detailed_scores = defaultdict(dict)
        
        # Traiter les résultats
        for i, task_type in enumerate(task_types):
            result = task_results[i]
            
            if task_type in {"hard_skills", "soft_skills", "experience", "languages"}:
                component_scores[task_type], detailed_scores[task_type] = result
            else:
                component_scores[task_type] = result
        
        # Calculer le score de langue (non asynchrone)
        if job.get("required_languages") and candidate.get("languages"):
            component_scores["languages"], detailed_scores["languages"] = self.calculate_language_score(
                candidate.get("languages", {}),
                job.get("required_languages", {})
            )
        
        # Calculer les scores divers (salaire et travail à distance)
        misc_scores = self.calculate_misc_scores(candidate, job)
        for key, value in misc_scores.items():
            component_scores[key] = value
        
        # Calculer le score final pondéré
        weighted_scores = {}
        for component, score in component_scores.items():
            weight = weights.get(component, 0.0)
            weighted_score = weight * score
            weighted_scores[component] = weighted_score
        
        cumulative_score = sum(weighted_scores.values())
        
        # Appliquer le bonus de tag
        final_score = cumulative_score * (1 + tag_bonus)
        
        # Calculer le temps de calcul
        computation_time = time.perf_counter() - start_time
        
        # Préparer le nombre d'appels API
        api_calls = self.cache_service.api_calls
        
        # Renvoyer les résultats détaillés
        return {
            'total_score': final_score,
            'component_scores': dict(component_scores),
            'weighted_scores': weighted_scores,
            'weights': weights,
            'detailed_scores': dict(detailed_scores),
            'tag_bonus': tag_bonus,
            'tags_common': list(common_tags),
            'api_calls': api_calls,
            'computation_time': computation_time
        }

# ============= 5. API ET INTERFACE WEB =============

# Créer des métriques API
REQUEST_COUNT = Counter('api_requests_total', 'Total des requêtes API', ['endpoint', 'method', 'status'])
REQUEST_LATENCY = Histogram('api_request_latency_seconds', 'Latence des requêtes API', ['endpoint'])
MATCH_SCORE = Histogram('match_scores', 'Distribution des scores de correspondance')
API_CALLS = Counter('openai_api_calls_total', 'Total des appels API OpenAI')
CACHE_HITS = Counter('cache_hits_total', 'Total des succès de cache')
CACHE_MISSES = Counter('cache_misses_total', 'Total des échecs de cache')

# Décorateur d'authentification par clé API
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not config.enable_api_key_auth:
            return f(*args, **kwargs)
        
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == config.api_key:
            return f(*args, **kwargs)
        else:
            abort(401, description="Clé API valide requise")
    
    return decorated_function

# Décorateur de chronométrage des requêtes
def time_request(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        endpoint = request.path
        start_time = time.perf_counter()
        
        try:
            response = await f(*args, **kwargs)
            status = response.status_code
        except Exception as e:
            status = 500
            raise e
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_COUNT.labels(endpoint=endpoint, method=request.method, status=status).inc()
            REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
        
        return response
    
    return decorated_function

# Créer des services
cache_service = CacheService(config)
openai_service = OpenAIService(config, cache_service)
matching_service = MatchingService(config, openai_service, cache_service)

# Créer l'application Flask
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
CORS(app)

# Créer un limiteur de débit
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[f"{config.api_rate_limit} per minute"]
)

# Créer des routes
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/metrics')
@require_api_key
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/api/v1/score', methods=['POST'])
@require_api_key
@time_request
async def score_endpoint():
    """
    Évaluer un seul candidat par rapport à un emploi.
    """
    try:
        # Valider la requête
        if not request.is_json:
            return jsonify({'error': 'Le Content-Type doit être application/json'}), 400
        
        data = request.get_json()
        
        if 'candidate' not in data or 'job' not in data:
            return jsonify({'error': 'La requête doit inclure un candidat et un emploi'}), 400
        
        candidate = data['candidate']
        job = data['job']
        
        # Anonymiser le candidat pour la conformité RGPD si activé
        if config.anonymize_data:
            candidate = anonymize_candidate(candidate)
        
        # Calculer le score de correspondance
        match_result = await matching_service.calculate_match_score(candidate, job)
        
        # Mettre à jour les métriques
        MATCH_SCORE.observe(match_result['total_score'])
        API_CALLS.inc(match_result['api_calls'])
        
        return jsonify({
            'candidate': candidate,
            'match_result': match_result
        })
    
    except Exception as e:
        logger.error(f"Erreur dans le point de terminaison de score: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/batch', methods=['POST'])
@require_api_key
@time_request
async def batch_score_endpoint():
    """
    Évaluer plusieurs candidats par rapport à un emploi et renvoyer les N meilleurs.
    """
    try:
        # Valider la requête
        if not request.is_json:
            return jsonify({'error': 'Le Content-Type doit être application/json'}), 400
        
        data = request.get_json()
        
        if 'candidates' not in data or 'job' not in data:
            return jsonify({'error': 'La requête doit inclure des candidats et un emploi'}), 400
        
        candidates = data['candidates']
        job = data['job']
        top_n = data.get('top_n', 10)
        
        if not isinstance(candidates, list):
            return jsonify({'error': 'Les candidats doivent être une liste'}), 400
        
        if top_n < 1:
            return jsonify({'error': 'top_n doit être un entier positif'}), 400
        
        # Traiter les candidats par lots
        all_results = []
        
        # Regrouper les candidats en lots pour le traitement
        batch_size = min(config.batch_size, len(candidates))
        batches = [candidates[i:i + batch_size] for i in range(0, len(candidates), batch_size)]
        
        for batch in batches:
            # Traiter les candidats par lot
            tasks = []
            
            for candidate in batch:
                # Anonymiser le candidat pour la conformité RGPD si activé
                if config.anonymize_data:
                    candidate = anonymize_candidate(candidate)
                
                # Créer une tâche pour le traitement
                tasks.append(matching_service.calculate_match_score(candidate, job))
            
            # Traiter le lot simultanément
            batch_results = await asyncio.gather(*tasks)
            
            # Combiner avec les candidats
            for i, result in enumerate(batch_results):
                candidate = batch[i]
                
                # Ajouter aux résultats
                all_results.append({
                    'candidate': candidate,
                    'match_result': result
                })
        
        # Trier les résultats par score
        sorted_results = sorted(
            all_results,
            key=lambda x: x['match_result']['total_score'],
            reverse=True
        )
        
        # Prendre les N meilleurs
        top_results = sorted_results[:top_n]
        
        # Générer un fichier de sortie
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"top_{top_n}_candidates_{timestamp}.json"
        filepath = os.path.join(config.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'top_candidates': top_results,
                'total_candidates': len(candidates),
                'job': job
            }, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour les métriques
        for result in top_results:
            MATCH_SCORE.observe(result['match_result']['total_score'])
        
        # Obtenir le nombre d'appels API
        api_calls = cache_service.api_calls
        API_CALLS.inc(api_calls)
        
        # Obtenir les statistiques de cache
        cache_stats = await cache_service.get_stats()
        CACHE_HITS.inc(cache_stats['cache']['hits'])
        CACHE_MISSES.inc(cache_stats['cache']['misses'])
        
        return jsonify({
            'status': 'success',
            'message': f'Traité {len(candidates)} candidats',
            'filename': filename,
            'top_candidates': top_results,
            'total_candidates': len(candidates),
            'api_calls': api_calls
        })
    
    except Exception as e:
        logger.error(f"Erreur dans le point de terminaison de score par lots: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/files/<filename>', methods=['GET'])
@require_api_key
def download_file(filename):
    """
    Télécharger un fichier de résultats.
    """
    try:
        # Valider le nom de fichier pour éviter la traversée de répertoire
        if not re.match(r'^[a-zA-Z0-9_\-\.]+route('/')
def home():
    return jsonify({
        'name': config.app_name,
        'version': config.app_version,
        'status': 'running'
    })

@app., filename):
            return jsonify({'error': 'Nom de fichier invalide'}), 400
        
        # Obtenir le chemin du fichier
        filepath = os.path.join(config.output_dir, filename)
        
        # Vérifier si le fichier existe
        if not os.path.isfile(filepath):
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        # Renvoyer le fichier
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
    
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement du fichier: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/cache/stats', methods=['GET'])
@require_api_key
async def cache_stats_endpoint():
    """
    Obtenir les statistiques du cache.
    """
    try:
        # Obtenir les statistiques du cache
        cache_stats = await cache_service.get_stats()
        
        # Obtenir les statistiques OpenAI
        openai_stats = await openai_service.get_stats()
        
        return jsonify({
            'cache': cache_stats,
            'openai': openai_stats
        })
    
    except Exception as e:
        logger.error(f"Erreur lors de l'obtention des statistiques du cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/cache/flush', methods=['POST'])
@require_api_key
async def cache_flush_endpoint():
    """
    Vider le cache.
    """
    try:
        # Vider le cache
        await cache_service.cache.flush()
        
        return jsonify({
            'status': 'success',
            'message': 'Cache vidé'
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du vidage du cache: {e}")
        return jsonify({'error': str(e)}), 500

# Gestionnaires d'erreurs
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': str(error.description)}), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': str(error.description)}), 401

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@app.errorhandler(429)
def ratelimit_handler(error):
    return jsonify({'error': 'Limite de débit dépassée'}), 429

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

# ============= 6. FONCTIONS UTILITAIRES =============

def normalize_text(text: str) -> str:
    """Normaliser le texte en convertissant en minuscules et en supprimant la ponctuation."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return ' '.join(text.split())

def anonymize_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Anonymiser les données du candidat pour la conformité RGPD.
    """
    if not isinstance(candidate, dict):
        return {}
    
    # Créer une copie
    anon_candidate = dict(candidate)
    
    # Générer un ID s'il n'est pas présent
    if 'id' not in anon_candidate:
        anon_candidate['id'] = str(uuid.uuid4())
    
    # Hacher le nom
    if 'name' in anon_candidate:
        anon_candidate['name'] = f"Candidate_{hashlib.md5(anon_candidate['name'].encode()).hexdigest()[:8]}"
    
    # Supprimer les champs sensibles
    for field in ['email', 'phone', 'address', 'social_media', 'photo']:
        if field in anon_candidate:
            del anon_candidate[field]
    
    return anon_candidate

# ============= 7. POINT D'ENTRÉE PRINCIPAL =============

def start_server():
    """Démarrer le serveur."""
    # Journaliser les informations de démarrage
    logger.info(f"Démarrage de {config.app_name} v{config.app_version}")
    logger.info(f"Environnement: {config.environment}")
    
    # Gérer les signaux
    def signal_handler(sig, frame):
        logger.info("Arrêt en cours...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Démarrer le serveur
    if config.environment == "production":
        # Utiliser le serveur de production
        serve(app, host="0.0.0.0", port=8080)
    else:
        # Utiliser le serveur de développement
        app.run(debug=config.debug, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    start_server()route('/')
def home():
    return jsonify({
        'name': config.app_name,
        'version': config.app_version,
        'status': 'running'
    })

@app.