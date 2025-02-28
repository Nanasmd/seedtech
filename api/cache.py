"""
SEED Tech - Système de Correspondance des Candidats
Gestion du cache pour optimiser les appels API
"""

import os
import pickle
from typing import Dict, Tuple, Any, List, Optional
from flask import jsonify

from api.config import (
    CACHE_DIR, MAX_CACHE_SIZE, NAME_CACHE_FILE, HARD_SKILLS_CACHE_FILE,
    SOFT_SKILLS_CACHE_FILE, DEGREE_DOMAIN_CACHE_FILE, DEBUG_MODE
)
from api.similarity import normalize_text

# Initialisation des caches vides
name_similarity_cache = {}
hard_skills_similarity_cache = {}
soft_skills_similarity_cache = {}
degree_domain_similarity_cache = {}

def load_cache(cache_file: str) -> Dict[Tuple[str, str], float]:
    """Charge un cache depuis un fichier. Renvoie un dictionnaire vide si le fichier n'existe pas."""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            if DEBUG_MODE:
                print(f"Erreur lors du chargement du cache depuis {cache_file}: {e}")
            return {}
    return {}

def save_cache(cache: Dict[Tuple[str, str], float], cache_file: str):
    """Sauvegarde un cache dans un fichier, en s'assurant que le cache ne dépasse pas la taille maximale."""
    try:
        # Si le cache dépasse la taille maximale, conserve uniquement les entrées les plus récentes
        if len(cache) > MAX_CACHE_SIZE:
            # Cette approche simple prend simplement les derniers éléments MAX_CACHE_SIZE
            cache = dict(list(cache.items())[-MAX_CACHE_SIZE:])
        
        # S'assure que le répertoire existe
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f)
    except Exception as e:
        if DEBUG_MODE:
            print(f"Erreur lors de la sauvegarde du cache dans {cache_file}: {e}")

def load_caches():
    """Charge tous les caches depuis les fichiers."""
    global name_similarity_cache, hard_skills_similarity_cache
    global soft_skills_similarity_cache, degree_domain_similarity_cache
    
    name_similarity_cache = load_cache(NAME_CACHE_FILE)
    hard_skills_similarity_cache = load_cache(HARD_SKILLS_CACHE_FILE)
    soft_skills_similarity_cache = load_cache(SOFT_SKILLS_CACHE_FILE)
    degree_domain_similarity_cache = load_cache(DEGREE_DOMAIN_CACHE_FILE)
    
    if DEBUG_MODE:
        print(f"Chargé {len(name_similarity_cache)} entrées de similarité de noms")
        print(f"Chargé {len(hard_skills_similarity_cache)} entrées de similarité de compétences techniques")
        print(f"Chargé {len(soft_skills_similarity_cache)} entrées de similarité de compétences générales")
        print(f"Chargé {len(degree_domain_similarity_cache)} entrées de similarité de domaines d'études")

def save_caches():
    """Sauvegarde tous les caches dans des fichiers."""
    save_cache(name_similarity_cache, NAME_CACHE_FILE)
    save_cache(hard_skills_similarity_cache, HARD_SKILLS_CACHE_FILE)
    save_cache(soft_skills_similarity_cache, SOFT_SKILLS_CACHE_FILE)
    save_cache(degree_domain_similarity_cache, DEGREE_DOMAIN_CACHE_FILE)

def get_cache_stats():
    """Obtient des statistiques sur l'utilisation du cache."""
    stats = {
        'name_similarity_cache': len(name_similarity_cache),
        'hard_skills_similarity_cache': len(hard_skills_similarity_cache),
        'soft_skills_similarity_cache': len(soft_skills_similarity_cache),
        'degree_domain_similarity_cache': len(degree_domain_similarity_cache),
        'cache_dir': CACHE_DIR,
        'max_cache_size': MAX_CACHE_SIZE
    }
    return jsonify(stats)

def get_hard_skills_cache(
    skill1: Optional[str] = None, 
    skill2: Optional[str] = None, 
    limit: int = 100, 
    offset: int = 0
):
    """Récupère les entrées du cache de similarité des compétences techniques."""
    if skill1 and skill2:
        # Recherche d'une paire spécifique
        key = tuple(sorted([normalize_text(skill1), normalize_text(skill2)]))
        if key in hard_skills_similarity_cache:
            return jsonify({
                'skill1': skill1,
                'skill2': skill2,
                'similarity': hard_skills_similarity_cache[key]
            })
        else:
            return jsonify({'error': 'Paire de compétences non trouvée dans le cache'}), 404
    else:
        # Retourne le contenu paginé du cache
        # Convertit le cache en liste pour la pagination
        cache_items = list(hard_skills_similarity_cache.items())
        paginated_items = cache_items[offset:offset+limit]
        
        # Formatage pour la réponse JSON
        result = []
        for (skill1, skill2), similarity in paginated_items:
            result.append({
                'skill1': skill1,
                'skill2': skill2,
                'similarity': similarity
            })
        
        return jsonify({
            'total': len(hard_skills_similarity_cache),
            'limit': limit,
            'offset': offset,
            'items': result
        })