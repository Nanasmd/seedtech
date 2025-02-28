"""
SEED Tech - Système de Correspondance des Candidats
Fonctions de calcul de similarité pour comparer textes, compétences, etc.
"""

import re
import string
from typing import Dict, Tuple, Any, Optional
from functools import lru_cache
from openai import OpenAI

from api.config import (
    OPENAI_API_KEY, DEFAULT_MODEL, TECH_SKILLS_RELATIONS, DEBUG_MODE
)
from api.database import (
    get_similarity_from_cache, save_similarity_to_cache
)

# Initialisation du client OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

def normalize_text(text: str) -> str:
    """Normalise le texte en le convertissant en minuscules et en supprimant la ponctuation."""
    if not text:
        return ""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text.strip()

def check_skills_relations(skill1: str, skill2: str) -> Optional[float]:
    """Vérifie si deux compétences sont liées sur la base de relations prédéfinies.
    Retourne un score de similarité ou None si aucune relation n'est trouvée."""
    norm_skill1 = normalize_text(skill1)
    norm_skill2 = normalize_text(skill2)
    
    # Si les compétences sont identiques, retourne une similarité parfaite
    if norm_skill1 == norm_skill2:
        return 1.0
    
    # Vérifie les relations directes dans notre base de connaissances
    for base_skill, related_skills in TECH_SKILLS_RELATIONS.items():
        if norm_skill1 == base_skill and norm_skill2 in related_skills:
            # Relation de base : similarité de 0.8-0.9 selon leur proximité
            return 0.85
        elif norm_skill2 == base_skill and norm_skill1 in related_skills:
            return 0.85
        elif norm_skill1 in related_skills and norm_skill2 in related_skills:
            # Si les deux sont liées à la même compétence de base : similarité de 0.7
            return 0.7
    
    # Aucune relation prédéfinie trouvée
    return None

@lru_cache(maxsize=1000)
def calculate_skill_similarity(skill1: str, skill2: str) -> float:
    """Calcule la similarité entre deux compétences en utilisant d'abord des relations prédéfinies
    et en se rabattant sur l'API OpenAI si nécessaire. Les résultats sont mis en cache."""
    # Vérifie si elles sont exactement identiques après normalisation
    if normalize_text(skill1) == normalize_text(skill2):
        return 1.0
    
    # Vérifie d'abord la valeur en cache
    cached_score = get_similarity_from_cache('hard_skills', skill1, skill2)
    if cached_score is not None:
        return cached_score
    
    # Vérifie les relations prédéfinies
    relation_score = check_skills_relations(skill1, skill2)
    if relation_score is not None:
        # Sauvegarde dans le cache pour une utilisation future
        save_similarity_to_cache('hard_skills', skill1, skill2, relation_score)
        return relation_score
    
    # Si aucune relation prédéfinie, utilise l'API OpenAI
    return semantic_similarity_chatgpt(
        skill1, 
        skill2, 
        'hard_skills',
        prompt_type="hard_skill"
    )

def semantic_similarity_chatgpt(
    text1: str, 
    text2: str, 
    cache_type: str,
    prompt_type: str = "general"
) -> float:
    """Calcule la similarité sémantique entre deux textes en utilisant l'API d'OpenAI.
    Les résultats sont mis en cache pour minimiser les appels API."""
    # Vérifie d'abord le cache
    cached_score = get_similarity_from_cache(cache_type, text1, text2)
    if cached_score is not None:
        return cached_score
    
    # Définit les prompts pour différents types de comparaisons
    prompts = {
        "general": (
            "Sur une échelle de 0 à 1, où 0 signifie 'pas du tout similaire' et 1 signifie 'identique', "
            f"évaluez la similarité entre ces deux textes :\nTexte 1 : {text1}\nTexte 2 : {text2}\n"
            "Répondez uniquement par le score numérique."
        ),
        "hard_skill": (
            "En tant qu'expert en recrutement tech, évaluez la similarité entre ces deux compétences techniques "
            f"sur une échelle de 0 à 1 :\nCompétence 1 : {text1}\nCompétence 2 : {text2}\n"
            "Si ce sont des compétences identiques ou étroitement liées (comme TypeScript et JavaScript), "
            "donnez un score élevé (>0.8). Si ce sont des compétences fondamentalement différentes "
            "(comme Python et Photoshop), donnez un score bas (<0.3). "
            "Tenez compte des relations exactes entre langages de programmation. "
            "Répondez uniquement par le score numérique."
        ),
        "job_title": (
            "Vous êtes un expert en recrutement IT/Tech. Évaluez la similarité entre ces deux titres de poste "
            f"sur une échelle de 0 à 1 :\nTitre 1 : {text1}\nTitre 2 : {text2}\n"
            "Considérez les domaines d'expertise et compétences impliquées, pas seulement les mots exacts. "
            "Répondez uniquement par le score numérique."
        ),
        "degree": (
            "En tant qu'expert en recrutement tech, évaluez la similarité entre ces deux domaines de formation "
            f"sur une échelle de 0 à 1 :\nDomaine 1 : {text1}\nDomaine 2 : {text2}\n"
            "Tenez compte des chevauchements de compétences et connaissances. "
            "Répondez uniquement par le score numérique."
        ),
        "soft_skill": (
            "Sur une échelle de 0 à 1, évaluez la similarité entre ces deux compétences comportementales "
            f"(soft skills) :\nCompétence 1 : {text1}\nCompétence 2 : {text2}\n"
            "Répondez uniquement par le score numérique."
        )
    }
    
    prompt = prompts.get(prompt_type, prompts["general"])
    
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,  # Réponses déterministes
            max_tokens=10,
            n=1,
            stop=None,
        )
        
        score_text = response.choices[0].message.content.strip()
        score_match = re.search(r"(\d+\.\d+|\d+)", score_text)
        
        if score_match:
            score = float(score_match.group(1).replace(',', '.'))
        else:
            # Score par défaut si l'analyse échoue
            score = 0.5
        
        # Sauvegarde dans le cache pour une utilisation future
        save_similarity_to_cache(cache_type, text1, text2, score)
        
        return score
    
    except Exception as e:
        if DEBUG_MODE:
            print(f"Erreur lors de l'obtention du score de similarité : {e}")
        # Retourne un score modéré en cas d'échec de l'API
        return 0.5

def get_name_similarity(name1: str, name2: str) -> float:
    """Obtient la similarité entre deux titres de poste ou noms."""
    if not name1 or not name2:
        return 0.0
    
    # Vérifie si ils sont exactement identiques après normalisation
    if normalize_text(name1) == normalize_text(name2):
        return 1.0
    
    # Vérifie d'abord le cache
    cached_score = get_similarity_from_cache('name', name1, name2)
    if cached_score is not None:
        return cached_score
    
    # Si pas dans le cache, utilise l'API
    return semantic_similarity_chatgpt(
        name1, 
        name2, 
        'name',
        prompt_type="job_title"
    )

def get_hard_skill_similarity(skill1: str, skill2: str) -> float:
    """Obtient la similarité entre deux compétences techniques."""
    if not skill1 or not skill2:
        return 0.0
    
    # Utilise la fonction de similarité de compétences optimisée/mise en cache
    return calculate_skill_similarity(skill1, skill2)

def get_soft_skill_similarity(skill1: str, skill2: str) -> float:
    """Obtient la similarité entre deux compétences générales."""
    if not skill1 or not skill2:
        return 0.0
    
    # Vérifie si elles sont exactement identiques après normalisation
    if normalize_text(skill1) == normalize_text(skill2):
        return 1.0
    
    # Vérifie d'abord le cache
    cached_score = get_similarity_from_cache('soft_skills', skill1, skill2)
    if cached_score is not None:
        return cached_score
    
    # Si pas dans le cache, utilise l'API
    return semantic_similarity_chatgpt(
        skill1, 
        skill2, 
        'soft_skills',
        prompt_type="soft_skill"
    )

def get_degree_similarity(degree1: str, degree2: str) -> float:
    """Obtient la similarité entre deux diplômes ou parcours éducatifs."""
    if not degree1 or not degree2:
        return 0.0
    
    # Vérifie si ils sont exactement identiques après normalisation
    if normalize_text(degree1) == normalize_text(degree2):
        return 1.0
    
    # Vérifie d'abord le cache
    cached_score = get_similarity_from_cache('degree_domain', degree1, degree2)
    if cached_score is not None:
        return cached_score
    
    # Si pas dans le cache, utilise l'API
    return semantic_similarity_chatgpt(
        degree1, 
        degree2, 
        'degree_domain',
        prompt_type="degree"
    )