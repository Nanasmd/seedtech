"""
SEED Tech - Système de Matching de Candidats
Point d'entrée principal de l'API pour le déploiement serverless sur Vercel
"""

import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import time

# Add the parent directory to sys.path to make the 'api' package importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules nécessaires
from api.config import DEBUG_MODE
try:
    from api.cache import (
        load_caches, get_cache_stats, get_hard_skills_cache,
        name_similarity_cache, hard_skills_similarity_cache, 
        soft_skills_similarity_cache, degree_domain_similarity_cache
    )
    from api.parsing import parse_workable_candidate, parse_workable_job
    from api.scoring import calculate_match_score, test_match
    from api.workable import (
        get_workable_jobs, get_workable_candidates,
        get_workable_job_detail, get_workable_candidate_detail,
        get_workable_job_candidates, export_top_matches
    )
    modules_loaded = True
except ImportError as e:
    print(f"Attention: Impossible de charger certains modules: {e}")
    modules_loaded = False

# Reste du code identique au fichier paste.txt
