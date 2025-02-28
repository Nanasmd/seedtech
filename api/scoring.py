"""
SEED Tech - Système de Correspondance des Candidats
Fonctions de notation pour calculer les scores de correspondance entre candidats et offres d'emploi
"""

import time
import re
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from api.config import (
    BASE_WEIGHTS, FIXED_FIELDS, LANGUAGE_LEVELS, DEGREE_LEVELS,
    DIPLOMA_ABBREVIATIONS, DEBUG_MODE
)
from api.similarity import (
    get_name_similarity, get_hard_skill_similarity,
    get_soft_skill_similarity, get_degree_similarity,
    normalize_text
)
from api.parsing import calculate_months, extract_text, extract_soft_skills
from api.database import save_match_result, get_match_result

# ============ Fonctions de Notation d'Expérience ============

def experience_duration_score(candidate_months: int, required_months: int) -> float:
    """Calcule un score basé sur le nombre de mois d'expérience d'un candidat
    par rapport à ce qui est requis."""
    if required_months <= 0:
        return 1.0
    return min(1.0, candidate_months / required_months)

def calculate_experience_score(
    candidate_exp: Dict[str, Any], 
    required_exp: Dict[str, Any]
) -> Tuple[float, Dict[str, float]]:
    """Calcule le score de correspondance entre l'expérience d'un candidat et une expérience requise."""
    name_score = get_name_similarity(candidate_exp.get('name', ''), required_exp.get('name', ''))
    duration_score = experience_duration_score(
        candidate_exp.get('months', 0), 
        required_exp.get('months', 0)
    )
    
    # Le titre est plus important que la durée pour la correspondance des expériences
    total_score = 0.6 * name_score + 0.4 * duration_score
    
    details = {
        'name_score': name_score,
        'duration_score': duration_score
    }
    
    return total_score, details

def compare_experiences(
    candidate_experiences: List[Dict[str, Any]], 
    required_experiences: List[Dict[str, Any]]
) -> Tuple[float, List[Dict[str, Any]]]:
    """Compare les expériences d'un candidat avec les expériences requises."""
    if not candidate_experiences or not required_experiences:
        return 0.0, []
    
    obligatory_scores = []
    recommended_scores = []
    experience_details = []
    
    for required_exp in required_experiences:
        best_score = 0.0
        best_subscores = {'name_score': 0.0, 'duration_score': 0.0}
        best_match_name = ""
        
        for candidate_exp in candidate_experiences:
            score, sub_scores = calculate_experience_score(candidate_exp, required_exp)
            if score > best_score:
                best_score = score
                best_subscores = sub_scores
                best_match_name = candidate_exp.get('name', '')
        
        category = required_exp.get('category', '').lower()
        
        if category == 'obligatoire':
            obligatory_scores.append(best_score)
        elif category == 'recommandée':
            recommended_scores.append(best_score)
        
        experience_details.append({
            'required_exp_name': required_exp.get('name', ''),
            'best_match_name': best_match_name,
            'category': category,
            'best_score': best_score,
            'sub_scores': best_subscores
        })
    
    # Calcule le score final avec une pondération appropriée
    obligatory_avg = np.mean(obligatory_scores) if obligatory_scores else None
    recommended_avg = np.mean(recommended_scores) if recommended_scores else None
    
    if obligatory_avg is not None and recommended_avg is not None:
        final_score = 0.7 * obligatory_avg + 0.3 * recommended_avg
    elif obligatory_avg is not None:
        final_score = obligatory_avg
    elif recommended_avg is not None:
        final_score = recommended_avg
    else:
        final_score = 0.0
    
    return final_score, experience_details

# ============ Fonctions de Comparaison des Compétences Techniques ============

def compare_hard_skills(
    candidate_skills: List[str], 
    required_skills: List[Dict[str, str]]
) -> Tuple[float, Dict[str, Any]]:
    """Compare les compétences techniques d'un candidat avec les compétences requises."""
    if not candidate_skills or not required_skills:
        return 0.0, {}
    
    obligatory_scores = []
    recommended_scores = []
    detailed_scores = {}
    
    # Seuil pour considérer une correspondance pour les compétences obligatoires
    THRESHOLD_OBLIGATORY = 0.8
    
    for job_skill_info in required_skills:
        job_skill = job_skill_info.get('skill', '')
        category = job_skill_info.get('category', '').lower()
        
        max_score = 0.0
        best_candidate_skill = None
        
        # Trouver la meilleure compétence correspondante du candidat
        for candidate_skill in candidate_skills:
            score = get_hard_skill_similarity(candidate_skill, job_skill)
            if score > max_score:
                max_score = score
                best_candidate_skill = candidate_skill
        
        # Appliquer le seuil pour les compétences obligatoires
        if category == 'obligatoire':
            if max_score < THRESHOLD_OBLIGATORY:
                final_score = 0.0
                best_candidate_skill = None
            else:
                final_score = max_score
            
            obligatory_scores.append(final_score)
        elif category == 'recommandé':
            recommended_scores.append(max_score)
        
        # Stocke les informations détaillées du score
        detailed_scores[job_skill] = {
            'candidate_skill': best_candidate_skill,
            'score': max_score if category == 'recommandé' else final_score,
            'category': category
        }
    
    # Calcule le score final avec une pondération appropriée
    obligatory_avg = np.mean(obligatory_scores) if obligatory_scores else None
    recommended_avg = np.mean(recommended_scores) if recommended_scores else None
    
    if obligatory_avg is not None and recommended_avg is not None:
        final_score = 0.7 * obligatory_avg + 0.3 * recommended_avg
    elif obligatory_avg is not None:
        final_score = obligatory_avg
    elif recommended_avg is not None:
        final_score = recommended_avg
    else:
        final_score = 0.0
    
    return final_score, detailed_scores

# ============ Fonctions de Comparaison des Compétences Générales ============

def compare_soft_skills(
    candidate_skills: List[str], 
    required_skills: List[str]
) -> Tuple[float, List[Dict[str, Any]]]:
    """Compare les compétences générales d'un candidat avec les compétences générales requises."""
    if not candidate_skills or not required_skills:
        return 0.0, []
    
    detailed_scores = []
    best_scores = []
    
    for candidate_skill in candidate_skills:
        scores = []
        for required_skill in required_skills:
            score = get_soft_skill_similarity(candidate_skill, required_skill)
            scores.append(score)
        
        if scores:
            best_score = max(scores)
            best_index = np.argmax(scores)
            best_required_skill = required_skills[best_index]
            
            best_scores.append(best_score)
            detailed_scores.append({
                'candidate_skill': candidate_skill,
                'required_skill': best_required_skill,
                'score': best_score
            })
    
    final_score = np.mean(best_scores) if best_scores else 0.0
    return final_score, detailed_scores

# ============ Fonctions de Notation de l'Éducation/Diplôme ============

def preprocess_diploma_name(diploma_name: str) -> str:
    """Prétraitement d'un nom de diplôme en développant les abréviations."""
    if not diploma_name:
        return ""
    
    result = diploma_name
    for abbr, full_term in DIPLOMA_ABBREVIATIONS.items():
        result = re.sub(r'\b' + abbr + r'\b', full_term, result, flags=re.IGNORECASE)
    
    return result

def extract_degree_level_and_field(degree_str: str) -> Tuple[str, str]:
    """Extrait le niveau et le domaine d'une chaîne de diplôme."""
    if not degree_str:
        return "", ""
    
    degree_str = degree_str.lower()
    level = ""
    field = degree_str
    
    # Extraire le niveau et le domaine
    for level_term, _ in sorted(DEGREE_LEVELS.items(), key=lambda x: len(x[0]), reverse=True):
        if degree_str.startswith(level_term):
            level = level_term
            field = degree_str[len(level_term):].strip()
            if field.startswith("en "):
                field = field[3:].strip()
            break
    
    # Si aucun niveau n'a été trouvé mais que le domaine contient "master", "licence", etc.
    if not level:
        for level_term in DEGREE_LEVELS:
            if level_term in degree_str:
                level = level_term
                parts = degree_str.split(level_term, 1)
                field = (parts[0] + parts[1]).strip()
                break
    
    return level, field

def diploma_score(
    candidate_degree: str, 
    required_degree: str
) -> Tuple[float, Dict[str, Any]]:
    """Calcule un score basé sur la correspondance entre le diplôme d'un candidat et le diplôme requis."""
    if not candidate_degree or not required_degree:
        return 0.0, {}
    
    # Prétraitement et extraction du niveau et du domaine
    candidate_degree = preprocess_diploma_name(candidate_degree)
    required_degree = preprocess_diploma_name(required_degree)
    
    candidate_level, candidate_field = extract_degree_level_and_field(candidate_degree)
    required_level, required_field = extract_degree_level_and_field(required_degree)
    
    # Obtenir les valeurs numériques pour les niveaux de diplôme
    candidate_level_value = DEGREE_LEVELS.get(candidate_level.lower(), 0)
    required_level_value = DEGREE_LEVELS.get(required_level.lower(), 0)
    
    # Calculer le score de niveau - les candidats avec un niveau supérieur à celui requis obtiennent un score complet
    if required_level_value > 0:
        level_score = min(1.0, candidate_level_value / required_level_value)
    else:
        level_score = 1.0 if candidate_level_value > 0 else 0.0
    
    # Calculer la similarité du domaine
    field_similarity = get_degree_similarity(candidate_field, required_field)
    
    # Le score final combine le niveau (plus important) et la similarité du domaine
    final_score = 0.7 * level_score + 0.3 * field_similarity
    
    details = {
        'candidate_level': candidate_level,
        'required_level': required_level,
        'level_score': level_score,
        'candidate_field': candidate_field,
        'required_field': required_field,
        'field_similarity': field_similarity
    }
    
    return final_score, details

# ============ Fonctions de Notation des Compétences Linguistiques ============

def language_score(
    candidate_level: str, 
    required_level: str, 
    is_required: bool
) -> float:
    """Calcule un score basé sur la compétence linguistique d'un candidat par rapport à ce qui est requis."""
    # Obtenir les valeurs numériques pour les niveaux de compétence
    candidate_level_value = LANGUAGE_LEVELS.get(candidate_level.lower(), 0)
    required_level_value = LANGUAGE_LEVELS.get(required_level.lower(), 0)
    
    # Calculer la différence de niveau de compétence
    level_diff = candidate_level_value - required_level_value
    
    # Le calcul du score dépend de si la langue est requise ou recommandée
    if is_required:
        if level_diff < 0:
            # Le candidat ne répond pas au niveau requis
            return max(0.0, 1.0 + (-0.4 * abs(level_diff)))
        else:
            # Le candidat répond ou dépasse le niveau requis (petit bonus)
            return min(1.0, 1.0 + (0.05 * level_diff))
    else:
        # Pour les langues recommandées, les pénalités sont plus faibles
        if level_diff < 0:
            return max(0.0, 1.0 + (-0.2 * abs(level_diff)))
        else:
            return min(1.0, 1.0 + (0.05 * level_diff))

def calculate_language_score(
    candidate_languages: Dict[str, str],
    required_languages: Dict[str, Dict[str, Any]]
) -> Tuple[float, Dict[str, Any]]:
    """Compare les compétences linguistiques d'un candidat avec les langues requises."""
    if not required_languages:
        return 0.0, {}
    
    required_scores = []
    recommended_scores = []
    detailed_scores = {}
    
    for language, details in required_languages.items():
        # Obtenir le niveau de langue et le statut d'exigence
        required_level = details.get('level', '')
        is_required = details.get('required', False)
        
        # Obtenir le niveau du candidat pour cette langue (par défaut à 'rien' si non spécifié)
        candidate_level = candidate_languages.get(language.lower(), 'rien')
        
        # Calculer le score pour cette langue
        score = language_score(candidate_level, required_level, is_required)
        
        # Ajouter à la liste appropriée en fonction du statut d'exigence
        if is_required:
            required_scores.append(score)
        else:
            recommended_scores.append(score)
        
        # Stocker les informations détaillées du score
        detailed_scores[language] = {
            'candidate_level': candidate_level,
            'required_level': required_level,
            'score': score,
            'required': is_required
        }
    
    # Calculer le score final avec une pondération appropriée
    required_avg = np.mean(required_scores) if required_scores else None
    recommended_avg = np.mean(recommended_scores) if recommended_scores else None
    
    if required_avg is not None and recommended_avg is not None:
        final_score = 0.7 * required_avg + 0.3 * recommended_avg
    elif required_avg is not None:
        final_score = required_avg
    elif recommended_avg is not None:
        final_score = recommended_avg
    else:
        final_score = 0.0
    
    return final_score, detailed_scores

# ============ Fonctions de Notation Supplémentaires ============

def salary_score(candidate_min_salary: float, job_salary: float) -> float:
    """Calcule un score basé sur le fait que le salaire d'un emploi répond au minimum d'un candidat."""
    if not candidate_min_salary or not job_salary:
        return 1.0  # Si les informations sur le salaire sont manquantes, ne pas pénaliser
    
    return 1.0 if job_salary >= candidate_min_salary else 0.0

def remote_work_score(candidate_wants_remote: bool, job_offers_remote: bool) -> float:
    """Calcule un score basé sur le fait que l'option de télétravail d'un emploi correspond à la préférence d'un candidat."""
    # Si les informations sont manquantes, ne pas pénaliser
    if candidate_wants_remote is None or job_offers_remote is None:
        return 1.0
    
    return 1.0 if candidate_wants_remote == job_offers_remote else 0.0

# ============ Poids Adaptatifs pour la Notation ============

def adaptive_weights(job: Dict[str, Any], base_weights: Dict[str, float] = None) -> Dict[str, float]:
    """Calcule des poids adaptatifs basés sur les critères d'emploi disponibles."""
    if base_weights is None:
        base_weights = BASE_WEIGHTS.copy()
    
    # Créer une copie des poids de base pour éviter de modifier l'original
    new_weights = dict(base_weights)
    
    # Déterminer quels champs sont manquants
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
    
    # Mettre les poids à 0 pour les champs absents
    for field in fields_absent:
        new_weights[field] = 0.0
    
    # Calculer la somme des poids pour les champs fixes qui sont présents
    fixed_sum = 0.0
    for field in FIXED_FIELDS:
        if field not in fields_absent:
            fixed_sum += new_weights[field]
        else:
            new_weights[field] = 0.0
    
    # Identifier les champs ajustables (ceux qui ne sont pas fixes et pas absents)
    adjustable_fields = []
    adjustable_sum = 0.0
    for field, weight in new_weights.items():
        if field not in FIXED_FIELDS and field not in fields_absent:
            adjustable_fields.append(field)
            adjustable_sum += weight
    
    # Calculer la masse totale à redistribuer
    sum_all = sum(base_weights.values())
    sum_current = fixed_sum + adjustable_sum
    mass_to_redistribute = sum_all - sum_current
    
    # Redistribuer proportionnellement aux champs ajustables
    if adjustable_sum > 0:
        ratio = (adjustable_sum + mass_to_redistribute) / adjustable_sum
        for field in adjustable_fields:
            new_weights[field] *= ratio
    
    # Vérifier que les poids somment à environ 1.0
    final_sum = sum(new_weights.values())
    if abs(final_sum - 1.0) > 1e-6 and DEBUG_MODE:
        print(f"[AVERTISSEMENT] Les poids finaux somment à {final_sum}, pas à 1.0")
    
    return new_weights

# ============ Fonction Principale de Correspondance ============

def calculate_match_score(
    candidate: Dict[str, Any], 
    job: Dict[str, Any],
    activate_tags: bool = True,
    save_result: bool = True
) -> Dict[str, Any]:
    """Calcule le score de correspondance global entre un candidat et un emploi.
    
    Args:
        candidate: Dictionnaire de données du candidat
        job: Dictionnaire de données de l'emploi
        activate_tags: Indique s'il faut utiliser le filtrage basé sur les tags
        save_result: Indique s'il faut sauvegarder le résultat de correspondance dans la base de données
        
    Returns:
        Score de correspondance et résultats détaillés
    """
    # Vérifier si nous avons un résultat en cache pour cet emploi et ce candidat
    candidate_id = candidate.get('id')
    job_id = job.get('id')
    
    if candidate_id and job_id:
        cached_result = get_match_result(job_id, candidate_id)
        if cached_result:
            # Retourner le résultat en cache s'il existe et est récent (moins d'un jour)
            if time.time() - cached_result['timestamp'] < 86400:  # 24 heures
                return cached_result['details']
    
    start_time = time.perf_counter()
    
    # Vérifier les tags communs si le filtrage basé sur les tags est actif
    if activate_tags:
        candidate_tags = set(tag.lower() for tag in candidate.get('tags', []))
        job_tags = set(tag.lower() for tag in job.get('tags', []))
        common_tags = candidate_tags.intersection(job_tags)
        num_common_tags = len(common_tags)
        
        # Si aucun tag commun et que le filtrage par tag est actif, retourner un score vide
        if num_common_tags == 0:
            result = {
                'total_score': 0.0,
                'reason': 'Aucun tag commun',
                'experience_score': 0.0,
                'experience_details': [],
                'degree_score': 0.0,
                'degree_details': {},
                'salary_score': 0.0,
                'remote_work_score': 0.0,
                'hard_skill_score': 0.0,
                'hard_skill_details': {},
                'language_score': 0.0,
                'language_details': {},
                'soft_skill_score': 0.0,
                'soft_skill_details': [],
                'tag_bonus': 0.0,
                'common_tags': []
            }
            
            # Sauvegarder le résultat dans la base de données si demandé
            if save_result and candidate_id and job_id:
                save_match_result(job_id, candidate_id, 0.0, result)
                
            return result
    else:
        # Si le filtrage par tag n'est pas actif, supposer qu'il n'y a pas de bonus de tag
        num_common_tags = 0
        common_tags = []
    
    # Calculer le bonus de tag (le cas échéant)
    tag_bonus = 0.0
    if num_common_tags == 2:
        tag_bonus = 0.05
    elif num_common_tags >= 3:
        tag_bonus = 0.10
    
    # Obtenir des poids adaptatifs basés sur les critères d'emploi disponibles
    weights = adaptive_weights(job)
    
    # Calculer des scores détaillés pour chaque catégorie
    with ThreadPoolExecutor() as executor:
        # Définir toutes les tâches de notation à exécuter en parallèle
        tasks = {
            'experience': executor.submit(
                compare_experiences,
                candidate.get('experiences', []),
                job.get('required_experiences', [])
            ),
            'degree': executor.submit(
                diploma_score,
                candidate.get('degree', ''),
                job.get('required_degree', '')
            ),
            'hard_skills': executor.submit(
                compare_hard_skills,
                candidate.get('hard_skills', []),
                job.get('hard_skills', [])
            ),
            'soft_skills': executor.submit(
                compare_soft_skills,
                candidate.get('soft_skills', []),
                job.get('required_soft_skills', [])
            ),
            'languages': executor.submit(
                calculate_language_score,
                candidate.get('languages', {}),
                job.get('required_languages', {})
            ),
            'salary': executor.submit(
                salary_score,
                candidate.get('min_salary', 0),
                job.get('salary', 0)
            ),
            'remote_work': executor.submit(
                remote_work_score,
                candidate.get('wants_remote', False),
                job.get('offers_remote', False)
            )
        }
        
        # Collecter les résultats au fur et à mesure qu'ils se terminent
        results = {}
        for category, future in tasks.items():
            try:
                results[category] = future.result()
            except Exception as e:
                if DEBUG_MODE:
                    print(f"Erreur lors du calcul du score {category}: {e}")
                # Définir des valeurs par défaut pour les calculs échoués
                if category in ['experience', 'hard_skills', 'soft_skills', 'languages', 'degree']:
                    results[category] = (0.0, [])
                else:
                    results[category] = 0.0
    
    # Extraire les scores et les détails des résultats parallèles
    exp_score, exp_details = results['experience']
    deg_score, deg_details = results['degree']
    hard_skill_score, hard_skill_details = results['hard_skills']
    soft_skill_score, soft_skill_details = results['soft_skills']
    language_score, language_details = results['languages']
    sal_score = results['salary']
    remote_score = results['remote_work']
    
    # Calculer le score total pondéré
    total_score = (
        weights['hard_skills'] * hard_skill_score +
        weights['soft_skills'] * soft_skill_score +
        weights['experience'] * exp_score +
        weights['degree'] * deg_score +
        weights['salary'] * sal_score +
        weights['remote_work'] * remote_score +
        weights['languages'] * language_score
    )
    
    # Appliquer le bonus de tag
    total_score *= (1 + tag_bonus)
    
    # Enregistrer le temps de calcul
    end_time = time.perf_counter()
    computation_time = end_time - start_time
    
    # Construire des résultats de correspondance complets
    result = {
        'total_score': total_score,
        'weighted_scores': {
            'hard_skills': weights['hard_skills'] * hard_skill_score,
            'soft_skills': weights['soft_skills'] * soft_skill_score,
            'experience': weights['experience'] * exp_score,
            'degree': weights['degree'] * deg_score,
            'salary': weights['salary'] * sal_score,
            'remote_work': weights['remote_work'] * remote_score,
            'languages': weights['languages'] * language_score
        },
        'weights': weights,
        'experience_score': exp_score,
        'experience_details': exp_details,
        'degree_score': deg_score,
        'degree_details': deg_details,
        'salary_score': sal_score,
        'remote_work_score': remote_score,
        'hard_skill_score': hard_skill_score,
        'hard_skill_details': hard_skill_details,
        'language_score': language_score,
        'language_details': language_details,
        'soft_skill_score': soft_skill_score,
        'soft_skill_details': soft_skill_details,
        'tag_bonus': tag_bonus,
        'common_tags': list(common_tags) if activate_tags else [],
        'computation_time': computation_time
    }
    
    # Sauvegarder le résultat dans la base de données si demandé
    if save_result and candidate_id and job_id:
        save_match_result(job_id, candidate_id, total_score, result)
    
    return result

def test_match():
    """Génère une correspondance de test pour les tests d'API."""
    # Données d'exemple de candidat
    candidate = {
        "id": "test_candidate_1",
        "name": "Jane Doe",
        "experiences": [
            {
                "name": "Développeur Full Stack",
                "months": 18,
                "description": "Développement d'applications web avec React et Node.js"
            },
            {
                "name": "Développeur Frontend",
                "months": 12,
                "description": "Création d'interfaces utilisateur avec Vue.js"
            }
        ],
        "degree": "Master en Informatique",
        "wants_remote": True,
        "min_salary": 35000,
        "hard_skills": ["JavaScript", "React", "Node.js", "Python", "Docker"],
        "soft_skills": ["Communication", "Travail d'équipe", "Résolution de problèmes"],
        "tags": ["full stack", "javascript", "développeur web"],
        "languages": {"français": "bilingue/maternelle", "anglais": "courant"}
    }
    
    # Données d'exemple d'emploi
    job = {
        "id": "test_job_1",
        "title": "Développeur FullStack JavaScript",
        "required_experiences": [
            {
                "name": "Développeur Web",
                "months": 12,
                "description": "Développement d'applications web modernes",
                "category": "obligatoire"
            },
            {
                "name": "DevOps",
                "months": 6,
                "description": "Mise en place de pipelines CI/CD",
                "category": "recommandée"
            }
        ],
        "required_degree": "Licence en Informatique",
        "offers_remote": True,
        "salary": 40000,
        "hard_skills": [
            {"skill": "JavaScript", "category": "obligatoire"},
            {"skill": "React", "category": "obligatoire"},
            {"skill": "Node.js", "category": "obligatoire"},
            {"skill": "Docker", "category": "recommandé"}
        ],
        "required_soft_skills": ["Communication", "Travail d'équipe"],
        "tags": ["full stack", "javascript", "node.js"],
        "required_languages": {
            "français": {"level": "courant", "required": True},
            "anglais": {"level": "intermédiaire", "required": False}
        }
    }
    
    # Calculer le score de correspondance mais ne pas sauvegarder dans la base de données
    return calculate_match_score(candidate, job, save_result=False)