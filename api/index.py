"""
SEED Tech - Système de Matching de Candidats
Point d'entrée principal de l'API pour le déploiement serverless sur Vercel
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import time

# Import des modules nécessaires
from api.config import DEBUG_MODE
from api.cache import (
    load_caches, get_cache_stats, get_hard_skills_cache,
    name_similarity_cache, hard_skills_similarity_cache, 
    soft_skills_similarity_cache, degree_domain_similarity_cache
)
from api.parsing import parse_workable_candidate, parse_workable_job
from api.scoring import calculate_match_score
from api.workable import (
    get_workable_jobs, get_workable_candidates,
    get_workable_job_detail, get_workable_candidate_detail,
    get_workable_job_candidates, export_top_matches
)

# Initialisation de l'application Flask (notre serveur web)
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)  # Permet une meilleure gestion quand on est derrière un proxy
CORS(app)  # Autorise les requêtes provenant d'autres sites web

# Ajout d'en-têtes de sécurité pour la conformité RGPD
@app.after_request
def add_header(response):
    # Protection contre diverses attaques web
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    # Empêche la mise en cache des données sensibles
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

# Chargement des caches au démarrage pour optimiser les performances
load_caches()

# Route d'accueil - page principale
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'service': 'API de Matching SEED Tech',
        'status': 'actif',
        'version': '1.0'
    })

# Route de test avec données d'exemple
@app.route('/test', methods=['GET'])
def test_route():
    # Permet de tester rapidement le système avec des données pré-configurées
    try:
        from api.scoring import test_match
        return jsonify(test_match())
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Calcul du score de compatibilité entre un candidat et une offre d'emploi
@app.route('/score', methods=['POST'])
def scoring():
    try:
        # Récupération des données JSON envoyées par l'utilisateur
        json_data = request.get_json()
        
        # Vérification que toutes les données nécessaires sont présentes
        if not json_data:
            return jsonify({'erreur': 'Aucune donnée fournie'}), 400
        
        if 'candidate' not in json_data or 'job' not in json_data:
            return jsonify({'erreur': 'Les données du candidat et de l\'offre sont nécessaires'}), 400
        
        # Extraction des données du candidat et de l'offre
        candidate = json_data["candidate"]
        job = json_data["job"]
        
        # Paramètres optionnels
        activate_tags = json_data.get('activate_tags', True)
        
        # Calcul du score de compatibilité
        match = calculate_match_score(candidate, job, activate_tags)
        
        # Renvoi des résultats
        return jsonify(match)
    
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Routes pour l'intégration avec Workable (ATS)

# Récupération de toutes les offres d'emploi
@app.route('/workable/jobs', methods=['GET'])
def workable_jobs_route():
    try:
        limit = request.args.get('limit', 50)
        return get_workable_jobs(limit)
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Récupération de tous les candidats
@app.route('/workable/candidates', methods=['GET'])
def workable_candidates_route():
    try:
        limit = request.args.get('limit', 50)
        return get_workable_candidates(limit)
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Récupération des détails d'une offre spécifique
@app.route('/workable/jobs/<string:job_shortcode>', methods=['GET'])
def workable_job_detail_route(job_shortcode):
    try:
        return get_workable_job_detail(job_shortcode)
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Récupération des détails d'un candidat spécifique
@app.route('/workable/candidates/<string:candidate_id>', methods=['GET'])
def workable_candidate_detail_route(candidate_id):
    try:
        return get_workable_candidate_detail(candidate_id)
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Récupération des candidats pour une offre spécifique
@app.route('/workable/jobs/<string:job_shortcode>/candidates', methods=['GET'])
def workable_job_candidates_route(job_shortcode):
    try:
        return get_workable_job_candidates(job_shortcode)
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Analyse de compatibilité entre une offre et tous ses candidats
@app.route('/match/job/<string:job_shortcode>', methods=['GET'])
def match_job_candidates_route(job_shortcode):
    try:
        # Nombre de meilleurs candidats à retourner
        top_n = int(request.args.get('top', 10))
        # Filtre sur les tags communs (activé/désactivé)
        activate_tags = request.args.get('activate_tags', 'false').lower() == 'true'
        
        # Calcul et renvoi des résultats
        from api.workable import match_job_with_candidates
        return jsonify(match_job_with_candidates(job_shortcode, top_n, activate_tags))
    
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Analyse de compatibilité entre un candidat et une offre spécifiques
@app.route('/match', methods=['GET'])
def match_candidate_job_route():
    try:
        # Paramètres de la requête
        job_shortcode = request.args.get('job_shortcode')
        candidate_id = request.args.get('candidate_id')
        activate_tags = request.args.get('activate_tags', 'true').lower() == 'true'
        
        # Vérification des paramètres obligatoires
        if not job_shortcode or not candidate_id:
            return jsonify({'erreur': 'Les identifiants de l\'offre et du candidat sont requis'}), 400
        
        # Calcul et renvoi des résultats
        from api.workable import match_candidate_with_job
        return jsonify(match_candidate_with_job(candidate_id, job_shortcode, activate_tags))
    
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Statistiques sur l'utilisation du cache
@app.route('/cache/stats', methods=['GET'])
def cache_stats_route():
    try:
        return get_cache_stats()
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Consultation du cache des compétences techniques
@app.route('/cache/hard_skills', methods=['GET'])
def hard_skills_cache_route():
    try:
        skill1 = request.args.get('skill1')
        skill2 = request.args.get('skill2')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        return get_hard_skills_cache(skill1, skill2, limit, offset)
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Export des meilleurs matchs pour une offre
@app.route('/export/top_matches/<string:job_shortcode>', methods=['POST'])
def export_top_matches_route(job_shortcode):
    try:
        top_n = int(request.args.get('top', 10))
        return export_top_matches(job_shortcode, top_n)
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500

# Démarrage du serveur
if __name__ == "__main__":
    # Détermination de l'environnement (développement ou production)
    env = os.getenv("ENV", "development").lower()
    
    if env == "production":
        # Mode production: Utilisation de waitress pour un serveur robuste
        from waitress import serve
        print(f"Démarrage du serveur en mode production sur le port {os.getenv('PORT', '8080')}")
        serve(app, host="0.0.0.0", port=int(os.getenv('PORT', '8080')))
    else:
        # Mode développement: Serveur intégré de Flask avec débogage
        print("Démarrage du serveur en mode développement sur le port 5000")
        app.run(debug=DEBUG_MODE, host="0.0.0.0", port=5000)