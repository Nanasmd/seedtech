"""
SEED Tech - Système de Correspondance des Candidats

Module de gestion de base de données avancé avec support PostgreSQL et Redis.
Fournit des mécanismes de mise en cache, de stockage et de récupération 
des résultats de correspondance de candidats.

Caractéristiques principales :
- Gestion de connexion de base de données via pooling
- Mise en cache multi-niveau (Redis + PostgreSQL)
- Stockage des résultats de similarité et de correspondance
- Optimisation des performances et de la persistance des données
"""

import os
import time
import json
import psycopg2  # type: ignore
from psycopg2 import pool  # type: ignore
from psycopg2 import extras  # type: ignore
from psycopg2.pool import SimpleConnectionPool # type: ignore
from psycopg2.extras import RealDictCursor # type: ignore
from typing import Dict, Any, List, Optional, Tuple, Union, Literal
from contextlib import contextmanager
import redis
from datetime import datetime



from api.config import (
    DEBUG_MODE, REDIS_URL, POSTGRES_URL, 
    CACHE_EXPIRY_SECONDS, MAX_CACHE_ENTRIES
)
from api.similarity import normalize_text

# ============ Gestionnaire de Connexions PostgreSQL ============
class PostgreSQLConnectionManager:
    """
    Gestionnaire de connexions PostgreSQL avec stratégie de pooling.
    
    Permet de gérer efficacement les connexions à la base de données :
    - Création d'un pool de connexions
    - Gestion des connexions et des transactions
    - Support du mode débogage
    """
    
    def __init__(
        self, 
        postgres_url: str, 
        min_connections: int = 1, 
        max_connections: int = 10
    ):
        """
        Initialise un pool de connexions PostgreSQL.
        
        Args:
            postgres_url (str): URL de connexion à la base de données
            min_connections (int): Nombre minimum de connexions dans le pool
            max_connections (int): Nombre maximum de connexions dans le pool
        """
        try:
            self.connection_pool = SimpleConnectionPool(
                minconn=min_connections,
                maxconn=max_connections,
                dsn=postgres_url
            )
            if DEBUG_MODE:
                print(f"Pool de connexions PostgreSQL initialisé avec succès")
        except Exception as e:
            if DEBUG_MODE:
                print(f"Échec de l'initialisation du pool PostgreSQL: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Gestionnaire de contexte pour obtenir une connexion du pool.
        
        Gère automatiquement :
        - L'acquisition d'une connexion
        - La validation ou l'annulation de la transaction
        - La libération de la connexion
        
        Yields:
            Connexion PostgreSQL avec curseur de type dictionnaire
        """
        conn = None
        try:
            conn = self.connection_pool.getconn()
            # Utilise un curseur qui retourne des résultats comme des dictionnaires
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def init_database(self):
        """
        Initialise la structure de la base de données.
        
        Crée les tables nécessaires si elles n'existent pas :
        - Caches de similarité pour différents types de données
        - Table de résultats de correspondance
        - Indexes pour optimiser les performances
        """
        with self.get_connection() as cursor:
            # Création des tables de cache de similarité
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS name_similarity_cache (
                id SERIAL PRIMARY KEY,
                text1 TEXT NOT NULL,
                text2 TEXT NOT NULL,
                score REAL NOT NULL,
                timestamp BIGINT NOT NULL,
                UNIQUE(text1, text2)
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS hard_skills_similarity_cache (
                id SERIAL PRIMARY KEY,
                text1 TEXT NOT NULL,
                text2 TEXT NOT NULL,
                score REAL NOT NULL,
                timestamp BIGINT NOT NULL,
                UNIQUE(text1, text2)
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS soft_skills_similarity_cache (
                id SERIAL PRIMARY KEY,
                text1 TEXT NOT NULL,
                text2 TEXT NOT NULL,
                score REAL NOT NULL,
                timestamp BIGINT NOT NULL,
                UNIQUE(text1, text2)
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS degree_domain_similarity_cache (
                id SERIAL PRIMARY KEY,
                text1 TEXT NOT NULL,
                text2 TEXT NOT NULL,
                score REAL NOT NULL,
                timestamp BIGINT NOT NULL,
                UNIQUE(text1, text2)
            )
            ''')
            
            # Création de la table des résultats de correspondance
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_results (
                id SERIAL PRIMARY KEY,
                job_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                total_score REAL NOT NULL,
                details JSONB NOT NULL,
                timestamp BIGINT NOT NULL,
                UNIQUE(job_id, candidate_id)
            )
            ''')
            
            # Création d'index pour améliorer les performances
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_name_cache ON name_similarity_cache(text1, text2)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hard_skills_cache ON hard_skills_similarity_cache(text1, text2)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_soft_skills_cache ON soft_skills_similarity_cache(text1, text2)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_degree_cache ON degree_domain_similarity_cache(text1, text2)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_match_job_candidate ON match_results(job_id, candidate_id)')

# Initialisation du gestionnaire de connexions PostgreSQL
pg_manager = PostgreSQLConnectionManager(POSTGRES_URL)

# ============ Configuration de la Connexion Redis ============
# Initialise la connexion Redis pour un cache de premier niveau
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL)
        if DEBUG_MODE:
            print(f"Connecté à Redis à {REDIS_URL}")
    except Exception as e:
        if DEBUG_MODE:
            print(f"Échec de connexion à Redis: {e}")

# ============ Fonctions Utilitaires de Gestion du Cache ============

def get_cache_key(cache_type: str, text1: str, text2: str) -> str:
    """
    Génère une clé de cache unique et cohérente pour Redis.
    
    Args:
        cache_type (str): Type de cache (nom, compétences, etc.)
        text1 (str): Premier texte à mettre en cache
        text2 (str): Deuxième texte à mettre en cache
    
    Returns:
        str: Clé de cache normalisée
    """
    sorted_texts = sorted([text1, text2])
    return f"{cache_type}:{sorted_texts[0]}:{sorted_texts[1]}"

def get_similarity_from_cache(
    cache_type: str, 
    text1: str, 
    text2: str
) -> Optional[float]:
    """
    Récupère un score de similarité en utilisant un cache multi-niveau.
    
    Stratégie :
    1. Vérifie d'abord dans Redis (cache rapide)
    2. Si non trouvé, recherche dans PostgreSQL
    
    Args:
        cache_type (str): Type de cache à interroger
        text1 (str): Premier texte
        text2 (str): Deuxième texte
    
    Returns:
        Optional[float]: Score de similarité si trouvé, None sinon
    """
    # Vérification dans Redis
    if redis_client:
        key = get_cache_key(cache_type, text1, text2)
        cached_value = redis_client.get(key)
        if cached_value:
            return float(cached_value)
    
    # Recherche dans PostgreSQL
    table_name = f"{cache_type}_similarity_cache"
    sorted_texts = sorted([text1, text2])
    text1, text2 = sorted_texts
    
    with pg_manager.get_connection() as cursor:
        cursor.execute(
            f"SELECT score FROM {table_name} WHERE text1 = %s AND text2 = %s",
            (text1, text2)
        )
        result = cursor.fetchone()
        
        if result:
            # Met à jour l'horodatage pour marquer l'entrée comme récente
            cursor.execute(
                f"UPDATE {table_name} SET timestamp = %s WHERE text1 = %s AND text2 = %s",
                (int(time.time()), text1, text2)
            )
            return result['score']
    
    return None

def save_similarity_to_cache(
    cache_type: str, 
    text1: str, 
    text2: str, 
    score: float
) -> None:
    """
    Enregistre un score de similarité dans les caches Redis et PostgreSQL.
    
    Stratégie de stockage :
    1. Stockage rapide dans Redis
    2. Stockage persistant dans PostgreSQL
    3. Gestion de la taille du cache
    
    Args:
        cache_type (str): Type de cache (nom, compétences, etc.)
        text1 (str): Premier texte
        text2 (str): Deuxième texte
        score (float): Score de similarité à stocker
    """
    # Stockage dans Redis si disponible
    if redis_client:
        key = get_cache_key(cache_type, text1, text2)
        redis_client.set(key, str(score), ex=CACHE_EXPIRY_SECONDS)
    
    # Stockage dans PostgreSQL
    table_name = f"{cache_type}_similarity_cache"
    
    # Normalisation de l'ordre des textes
    sorted_texts = sorted([text1, text2])
    text1, text2 = sorted_texts
    
    now = int(time.time())
    
    with pg_manager.get_connection() as cursor:
        # Gestion de la taille du cache
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()['count']
        
        if count >= MAX_CACHE_ENTRIES:
            # Suppression des entrées les plus anciennes
            num_to_delete = int(MAX_CACHE_ENTRIES * 0.1)
            cursor.execute(
                f"""
                DELETE FROM {table_name} 
                WHERE id IN (
                    SELECT id FROM {table_name} 
                    ORDER BY timestamp ASC 
                    LIMIT %s
                )
                """,
                (num_to_delete,)
            )
        
        # Insertion ou mise à jour de l'entrée
        cursor.execute(
            f"""
            INSERT INTO {table_name} (text1, text2, score, timestamp)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (text1, text2) DO UPDATE SET
                score = EXCLUDED.score,
                timestamp = EXCLUDED.timestamp
            """,
            (text1, text2, score, now)
        )

# [Autres fonctions de gestion de base de données]
def save_match_result(
    job_id: str,
    candidate_id: str,
    total_score: float,
    details: Dict[str, Any]
) -> int:
    """
    Enregistre un résultat de correspondance candidat-poste.
    
    Args:
        job_id (str): Identifiant unique de l'offre d'emploi
        candidate_id (str): Identifiant unique du candidat
        total_score (float): Score total de correspondance
        details (Dict[str, Any]): Détails de la correspondance
    
    Returns:
        int: ID de l'enregistrement inséré/mis à jour
    """
    now = int(time.time())
    
    with pg_manager.get_connection() as cursor:
        cursor.execute(
            """
            INSERT INTO match_results (job_id, candidate_id, total_score, details, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (job_id, candidate_id) DO UPDATE SET
                total_score = EXCLUDED.total_score,
                details = EXCLUDED.details,
                timestamp = EXCLUDED.timestamp
            RETURNING id
            """,
            (job_id, candidate_id, total_score, json.dumps(details), now)
        )
        
        result = cursor.fetchone()
        return result['id']

def get_match_result(
    job_id: str,
    candidate_id: str
) -> Optional[Dict[str, Any]]:
    """
    Récupère un résultat de correspondance spécifique.
    
    Args:
        job_id (str): Identifiant unique de l'offre d'emploi
        candidate_id (str): Identifiant unique du candidat
    
    Returns:
        Optional[Dict[str, Any]]: Détails du résultat de correspondance
    """
    with pg_manager.get_connection() as cursor:
        cursor.execute(
            """
            SELECT id, job_id, candidate_id, total_score, details, timestamp
            FROM match_results
            WHERE job_id = %s AND candidate_id = %s
            """,
            (job_id, candidate_id)
        )
        result = cursor.fetchone()
        
        if result:
            return {
                'id': result['id'],
                'job_id': result['job_id'],
                'candidate_id': result['candidate_id'],
                'total_score': result['total_score'],
                'details': json.loads(result['details']),
                'timestamp': result['timestamp'],
                'datetime': datetime.fromtimestamp(result['timestamp']).isoformat()
            }
        
        return None

def get_top_matches_for_job(
    job_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Récupère les meilleures correspondances pour une offre d'emploi.
    
    Args:
        job_id (str): Identifiant unique de l'offre d'emploi
        limit (int): Nombre maximum de correspondances à retourner
    
    Returns:
        List[Dict[str, Any]]: Liste des meilleures correspondances
    """
    with pg_manager.get_connection() as cursor:
        cursor.execute(
            """
            SELECT id, job_id, candidate_id, total_score, details, timestamp
            FROM match_results
            WHERE job_id = %s
            ORDER BY total_score DESC
            LIMIT %s
            """,
            (job_id, limit)
        )
        results = cursor.fetchall()
        
        return [{
            'id': result['id'],
            'job_id': result['job_id'],
            'candidate_id': result['candidate_id'],
            'total_score': result['total_score'],
            'details': json.loads(result['details']),
            'timestamp': result['timestamp'],
            'datetime': datetime.fromtimestamp(result['timestamp']).isoformat()
        } for result in results]

def get_cache_stats() -> Dict[str, Any]:
    """
    Récupère des statistiques détaillées sur l'utilisation du cache.
    
    Returns:
        Dict[str, Any]: Statistiques de cache Redis et PostgreSQL
    """
    stats = {}
    
    # Statistiques Redis
    if redis_client:
        try:
            info = redis_client.info()
            stats['redis'] = {
                'used_memory': info['used_memory_human'],
                'connected_clients': info['connected_clients'],
                'uptime_in_days': info['uptime_in_days']
            }
        except Exception as e:
            stats['redis'] = {'error': str(e)}
    
    # Statistiques PostgreSQL
    with pg_manager.get_connection() as cursor:
        for cache_type in ['name', 'hard_skills', 'soft_skills', 'degree_domain']:
            table_name = f"{cache_type}_similarity_cache"
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            stats[f"{cache_type}_cache_size"] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM match_results")
        stats['match_results_count'] = cursor.fetchone()['count']
    
    return stats

def get_hard_skills_cache(
    skill1: Optional[str] = None, 
    skill2: Optional[str] = None, 
    limit: int = 100, 
    offset: int = 0
) -> Union[Dict[str, Any], Tuple[Dict[str, Any], Literal[404]]]:
    """
    Récupère les entrées du cache de compétences techniques.
    
    Args:
        skill1 (Optional[str]): Premier libellé de compétence
        skill2 (Optional[str]): Deuxième libellé de compétence
        limit (int): Nombre maximum d'entrées à retourner
        offset (int): Décalage pour la pagination
    
    Returns:
        Union[Dict[str, Any], Tuple[Dict[str, Any], Literal[404]]]: 
        Résultats de cache ou message d'erreur
    """
    if skill1 and skill2:
        # Recherche d'une paire spécifique de compétences
        key = tuple(sorted([normalize_text(skill1), normalize_text(skill2)]))
        if key in hard_skills_similarity_cache:
            # Retourne la similarité si la paire est trouvée dans le cache
            return {
                'skill1': skill1,
                'skill2': skill2,
                'similarity': hard_skills_similarity_cache[key]
            }
        else:
            # Retourne une erreur 404 si la paire n'est pas trouvée
            return {'error': 'Paire de compétences non trouvée dans le cache'}, 404
    else:
        # Retourne le contenu paginé du cache
        with pg_manager.get_connection() as cursor:
            # Obtient le nombre total d'entrées dans le cache
            cursor.execute("SELECT COUNT(*) as count FROM hard_skills_similarity_cache")
            total = cursor.fetchone()['count']
            
            # Récupère les éléments paginés
            cursor.execute(
                """
                SELECT text1, text2, score
                FROM hard_skills_similarity_cache
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            
            # Transforme les résultats en liste de dictionnaires
            items = [{
                'skill1': row['text1'],
                'skill2': row['text2'],
                'similarity': row['score']
            } for row in cursor.fetchall()]
            
            # Retourne un dictionnaire avec les informations de pagination
            return {
                'total': total,
                'limit': limit,
                'offset': offset,
                'items': items
            }

def load_caches():
    """
    Charge les caches depuis la base de données au démarrage.
    
    Note: Dans l'implémentation PostgreSQL, cette fonction 
    est principalement un espace réservé car le chargement 
    se fait à la demande.
    """
    global name_similarity_cache, hard_skills_similarity_cache
    global soft_skills_similarity_cache, degree_domain_similarity_cache
    
    if DEBUG_MODE:
        print("Les caches seront chargés depuis la base de données selon les besoins")

# Initialisation des caches globaux pour compatibilité
hard_skills_similarity_cache = {}
name_similarity_cache = {}
soft_skills_similarity_cache = {}
degree_domain_similarity_cache = {}

# Initialise la base de données lors de l'importation du module
pg_manager.init_database()

# Documentation de configuration requise
"""
Configuration requise pour l'utilisation optimale :

Dépendances :
- psycopg2-binary
- redis
- python-dotenv

Variables d'environnement nécessaires :
- POSTGRES_URL : URL de connexion à PostgreSQL
- REDIS_URL : URL de connexion à Redis (optionnel)
- DEBUG_MODE : Active/désactive le mode débogage
- CACHE_EXPIRY_SECONDS : Durée d'expiration du cache Redis
- MAX_CACHE_ENTRIES : Nombre maximum d'entrées dans le cache

Exemple de configuration .env :
POSTGRES_URL=postgresql://utilisateur:motdepasse@localhost:5432/seed_tech_db
REDIS_URL=redis://localhost:6379/0
DEBUG_MODE=False
CACHE_EXPIRY_SECONDS=604800
MAX_CACHE_ENTRIES=100000
"""