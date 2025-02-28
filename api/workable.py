"""
SEED Tech - Système de Correspondance des Candidats
Intégration de l'API Workable pour récupérer candidats et offres d'emploi avec support de base de données
"""

import json
import time
import requests
from datetime import datetime
from flask import jsonify
from typing import Dict, Any, List, Optional, Union

from api.config import WORKABLE_API_KEY, API_CALL_DELAY, DEBUG_MODE
from api.parsing import parse_workable_candidate, parse_workable_job
from api.scoring import calculate_match_score
from api.database import save_match_result, get_match_result, get_top_matches_for_job

def get_workable_headers() -> Dict[str, str]:
    """Obtient les en-têtes requis pour les requêtes à l'API Workable."""
    if not WORKABLE_API_KEY:
        raise ValueError("Clé API Workable non configurée")
    
    return {
        "accept": "application/json",
        "Authorization": f"Bearer {WORKABLE_API_KEY}"
    }

def get_workable_jobs(limit: int = 50) -> Dict[str, Any]:
    """Récupère toutes les offres d'emploi depuis l'API Workable."""
    try:
        # Configuration des paramètres de requête
        url = "https://seed-tech.workable.com/spi/v3/jobs"
        headers = get_workable_headers()
        params = {"limit": limit}
        
        # Effectue la requête API
        response = requests.get(url, headers=headers, params=params)
        
        # Vérifie la réponse
        if response.status_code != 200:
            return {
                'error': f'Erreur API Workable: {response.status_code}',
                'details': response.text
            }
        
        # Retourne les offres d'emploi
        jobs = response.json()
        return jobs
    
    except Exception as e:
        return {'error': str(e)}

def get_workable_candidates(limit: int = 50) -> Dict[str, Any]:
    """Récupère tous les candidats depuis l'API Workable."""
    try:
        # Configuration des paramètres de requête
        url = "https://seed-tech.workable.com/spi/v3/candidates"
        headers = get_workable_headers()
        params = {"limit": limit}
        
        # Effectue la requête API
        response = requests.get(url, headers=headers, params=params)
        
        # Vérifie la réponse
        if response.status_code != 200:
            return {
                'error': f'Erreur API Workable: {response.status_code}',
                'details': response.text
            }
        
        # Retourne les candidats
        candidates = response.json()
        return candidates
    
    except Exception as e:
        return {'error': str(e)}

def get_workable_job_detail(job_shortcode: str) -> Dict[str, Any]:
    """Récupère les détails d'une offre d'emploi depuis l'API Workable."""
    try:
        # Configuration de la requête
        url = f"https://seed-tech.workable.com/spi/v3/jobs/{job_shortcode}"
        headers = get_workable_headers()
        
        # Effectue la requête API
        response = requests.get(url, headers=headers)
        
        # Vérifie la réponse
        if response.status_code != 200:
            return {
                'error': f'Erreur API Workable: {response.status_code}',
                'details': response.text
            }
        
        # Retourne les données de l'offre d'emploi
        job_data = response.json()
        # Ajoute le champ ID pour le stockage en base de données
        job_data['id'] = job_shortcode
        
        return job_data
    
    except Exception as e:
        return {'error': str(e)}

def get_workable_candidate_detail(candidate_id: str) -> Dict[str, Any]:
    """Récupère les détails d'un candidat depuis l'API Workable."""
    try:
        # Configuration de la requête
        url = f"https://seed-tech.workable.com/spi/v3/candidates/{candidate_id}"
        headers = get_workable_headers()
        
        # Effectue la requête API
        response = requests.get(url, headers=headers)
        
        # Vérifie la réponse
        if response.status_code != 200:
            return {
                'error': f'Erreur API Workable: {response.status_code}',
                'details': response.text
            }
        
        # Retourne les données du candidat
        candidate_data = response.json()
        # Ajoute le champ ID pour le stockage en base de données
        candidate_data['id'] = candidate_id
        
        return candidate_data
    
    except Exception as e:
        return {'error': str(e)}

def get_workable_job_candidates(job_shortcode: str) -> Dict[str, Any]:
    """Récupère les candidats pour une offre d'emploi spécifique depuis l'API Workable."""
    try:
        # Configuration de la requête
        url = f"https://seed-tech.workable.com/spi/v3/jobs/{job_shortcode}/candidates"
        headers = get_workable_headers()
        
        # Effectue la requête API
        response = requests.get(url, headers=headers)
        
        # Vérifie la réponse
        if response.status_code != 200:
            return {
                'error': f'Erreur API Workable: {response.status_code}',
                'details': response.text
            }
        
        # Retourne les données des candidats
        candidates_data = response.json()
        return candidates_data
    
    except Exception as e:
        return {'error': str(e)}

def add_workable_comment(candidate_id: str, job_shortcode: str, comment: str) -> Dict[str, Any]:
    """Ajoute un commentaire à un candidat dans Workable."""
    try:
        # Configuration de la requête
        url = f"https://seed-tech.workable.com/spi/v3/candidates/{candidate_id}/comments"
        headers = get_workable_headers()
        headers["Content-Type"] = "application/json"
        
        # Préparation des données du commentaire
        data = {
            "comment": {
                "body": comment,
                "jobShortcode": job_shortcode
            }
        }
        
        # Effectue la requête API
        response = requests.post(url, headers=headers, json=data)
        
        # Vérifie la réponse
        if response.status_code not in [200, 201]:
            return {
                'error': f'Erreur API Workable: {response.status_code}',
                'details': response.text
            }
        
        # Retourne la réponse de succès
        return {
            'success': True,
            'message': 'Commentaire ajouté avec succès'
        }
    
    except Exception as e:
        return {'error': str(e)}

def match_job_with_candidates(job_shortcode: str, top_n: int = 10, activate_tags: bool = False) -> Dict[str, Any]:
    """Calcule les scores de correspondance pour tous les candidats pour une offre d'emploi.
    
    Cette fonction essaie d'utiliser les résultats de correspondance existants de la base de données lorsque c'est possible,
    en recalculant uniquement pour les candidats qui n'ont pas de résultats récents.
    
    Args:
        job_shortcode: Code court de l'offre d'emploi à faire correspondre
        top_n: Nombre de meilleures correspondances à retourner
        activate_tags: Indique s'il faut filtrer par tags communs
        
    Returns:
        Dictionnaire avec les résultats de correspondance
    """
    try:
        # Vérifie d'abord si nous avons déjà des résultats de correspondance récents dans la base de données
        top_matches = get_top_matches_for_job(job_shortcode, top_n)
        
        # Si nous avons des résultats récents pour suffisamment de candidats, utilisons-les
        if len(top_matches) >= top_n:
            # Formate les résultats pour la réponse API
            return {
                'job_id': job_shortcode,
                'total_candidates': len(top_matches),
                'processed_candidates': len(top_matches),
                'top_matches': top_matches,
                'source': 'database'
            }
        
        # Sinon, calcule de nouvelles correspondances
        # Récupère les détails de l'offre d'emploi
        job_data = get_workable_job_detail(job_shortcode)
        if 'error' in job_data:
            return job_data
        
        parsed_job = parse_workable_job(job_data)
        parsed_job['id'] = job_shortcode  # S'assure que l'ID est défini pour la base de données
        
        # Récupère les candidats pour cette offre d'emploi
        candidates_data = get_workable_job_candidates(job_shortcode)
        if 'error' in candidates_data:
            return candidates_data
        
        candidate_summaries = candidates_data.get('candidates', [])
        
        # Traite chaque candidat
        matches = []
        for candidate_summary in candidate_summaries:
            try:
                # Vérifie d'abord si nous avons un résultat récent dans la base de données
                existing_match = get_match_result(job_shortcode, candidate_summary['id'])
                if existing_match and time.time() - existing_match['timestamp'] < 86400:  # 24 heures
                    # Utilise la correspondance existante si elle est récente
                    matches.append({
                        'candidate_id': candidate_summary['id'],
                        'candidate_name': existing_match['details'].get('candidate_name', ''),
                        'score': existing_match['total_score'],
                        'details': existing_match['details'],
                        'source': 'database'
                    })
                    continue
                
                # Sinon, calcule une nouvelle correspondance
                # Respecte les limites de taux d'API
                time.sleep(API_CALL_DELAY)
                
                # Récupère les données détaillées du candidat
                candidate_data = get_workable_candidate_detail(candidate_summary['id'])
                if 'error' in candidate_data:
                    continue
                
                parsed_candidate = parse_workable_candidate(candidate_data)
                parsed_candidate['id'] = candidate_summary['id']  # S'assure que l'ID est défini pour la base de données
                
                # Calcule le score de correspondance et sauvegarde dans la base de données
                match_result = calculate_match_score(parsed_candidate, parsed_job, activate_tags=activate_tags)
                
                # Ajoute les informations du candidat aux résultats de correspondance pour la réponse API
                match_info = {
                    'candidate_id': candidate_summary['id'],
                    'candidate_name': parsed_candidate['name'],
                    'score': match_result['total_score'],
                    'details': match_result,
                    'source': 'fresh_calculation'
                }
                
                matches.append(match_info)
            
            except Exception as e:
                if DEBUG_MODE:
                    print(f"Erreur lors du traitement du candidat {candidate_summary['id']}: {e}")
                continue
        
        # Trie par score (décroissant)
        sorted_matches = sorted(matches, key=lambda x: x['score'], reverse=True)
        
        # Retourne les meilleures correspondances
        return {
            'job_id': job_shortcode,
            'job_title': job_data.get('title', ''),
            'total_candidates': len(candidate_summaries),
            'processed_candidates': len(matches),
            'top_matches': sorted_matches[:top_n]
        }
    
    except Exception as e:
        return {'error': str(e)}

def match_candidate_with_job(candidate_id: str, job_shortcode: str, activate_tags: bool = True) -> Dict[str, Any]:
    """Calcule le score de correspondance entre un candidat spécifique et une offre d'emploi."""
    try:
        # Vérifie d'abord si nous avons un résultat récent dans la base de données
        existing_match = get_match_result(job_shortcode, candidate_id)
        if existing_match and time.time() - existing_match['timestamp'] < 86400:  # 24 heures
            # Ajoute les informations de source à la réponse
            result = existing_match['details']
            result['source'] = 'database'
            return result
        
        # Récupère les détails de l'offre d'emploi
        job_data = get_workable_job_detail(job_shortcode)
        if 'error' in job_data:
            return job_data
            
        # Récupère les détails du candidat
        candidate_data = get_workable_candidate_detail(candidate_id)
        if 'error' in candidate_data:
            return candidate_data
        
        # Analyse les données pour la mise en correspondance
        parsed_job = parse_workable_job(job_data)
        parsed_job['id'] = job_shortcode  # S'assure que l'ID est défini pour la base de données
        
        parsed_candidate = parse_workable_candidate(candidate_data)
        parsed_candidate['id'] = candidate_id  # S'assure que l'ID est défini pour la base de données
        
        # Calcule le score de correspondance et sauvegarde dans la base de données
        match = calculate_match_score(parsed_candidate, parsed_job, activate_tags=activate_tags)
        
        # Ajoute les informations de source à la réponse
        match['source'] = 'fresh_calculation'
        
        # Ajoute les informations de l'offre d'emploi et du candidat pour référence
        match['job_shortcode'] = job_shortcode
        match['job_title'] = job_data.get('title', '')
        match['candidate_id'] = candidate_id
        match['candidate_name'] = parsed_candidate['name']
        
        return match
    
    except Exception as e:
        return {'error': str(e)}

def export_top_matches(job_shortcode: str, top_n: int = 10) -> Dict[str, Any]:
    """Exporte les meilleures correspondances pour une offre d'emploi et génère un rapport.
    
    Cette fonction :
    1. Calcule les scores de correspondance pour tous les candidats (ou utilise les résultats en cache)
    2. Trie les résultats par score
    3. Génère un rapport texte formaté
    4. Sauvegarde les résultats dans un fichier JSON
    
    Args:
        job_shortcode: Code court de l'offre d'emploi
        top_n: Nombre de meilleures correspondances à inclure
        
    Returns:
        Dictionnaire avec les résultats d'exportation
    """
    try:
        # Récupère les correspondances de l'offre d'emploi et des candidats
        matches_result = match_job_with_candidates(job_shortcode, top_n)
        
        if 'error' in matches_result:
            return matches_result
        
        job_title = matches_result.get('job_title', job_shortcode)
        top_matches = matches_result.get('top_matches', [])
        
        # Génère le texte du commentaire
        comment_text = f"## SEED Tech - Top {top_n} Correspondances de Candidats\n\n"
        comment_text += f"Offre d'emploi : {job_title}\n"
        comment_text += f"Date : {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        for i, match in enumerate(top_matches, 1):
            score_percent = round(match['score'] * 100, 1)
            details = match.get('details', {})
            
            comment_text += (
                f"{i}. **{match.get('candidate_name', '')}** - {score_percent}%\n"
                f"   - Compétences techniques : {round(details.get('hard_skill_score', 0) * 100, 1)}%\n"
                f"   - Expérience : {round(details.get('experience_score', 0) * 100, 1)}%\n"
                f"   - Formation : {round(details.get('degree_score', 0) * 100, 1)}%\n"
                f"   - Langues : {round(details.get('language_score', 0) * 100, 1)}%\n\n"
            )
        
        # Prépare les données d'exportation
        export_data = {
            'job_shortcode': job_shortcode,
            'job_title': job_title,
            'match_date': datetime.now().strftime('%Y-%m-%d'),
            'total_candidates': matches_result.get('total_candidates', 0),
            'processed_candidates': matches_result.get('processed_candidates', 0),
            'top_matches': top_matches
        }
        
        # Retourne la réponse de succès
        return {
            'success': True,
            'job_shortcode': job_shortcode,
            'job_title': job_title,
            'exported_matches': len(top_matches),
            'match_summary': comment_text,
            'data': export_data
        }
    
    except Exception as e:
        return {'error': str(e)}