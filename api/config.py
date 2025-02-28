"""
SEED Tech - Système de Matching de Candidats
Paramètres de configuration de l'application
"""

import os
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis le fichier .env
load_dotenv()

# Clés API (sensibles - ne pas partager)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Clé pour l'intelligence artificielle
WORKABLE_API_KEY = os.getenv("WORKABLE_API_KEY")  # Clé pour accéder à Workable

# Configuration de la base de données
DATABASE_URL = os.getenv('POSTGRES_URL')  # Emplacement du fichier de base de données
REDIS_URL = os.getenv('REDIS_URL')  # Connexion au cache Redis (optionnel)
CACHE_EXPIRY_SECONDS = int(os.getenv('CACHE_EXPIRY_SECONDS', 604800))  # Durée de validité du cache (1 semaine)
MAX_CACHE_ENTRIES = int(os.getenv('MAX_CACHE_ENTRIES', 100000))  # Nombre maximum d'entrées en cache
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

# Configuration du matching
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))  # Seuil de similarité minimum
API_CALL_DELAY = float(os.getenv("API_CALL_DELAY", "0.2"))  # Délai entre appels API (secondes)

# Configuration OpenAI
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")  # Modèle d'IA à utiliser

# Configuration de l'application
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"  # Mode débogage (plus verbeux)

# Création des répertoires nécessaires
os.makedirs(os.path.dirname(DATABASE_URL), exist_ok=True)

# Poids de base pour les différentes dimensions du matching
# Ces coefficients déterminent l'importance relative de chaque critère
BASE_WEIGHTS = {
    'hard_skills': 0.40,  # 40% pour les compétences techniques (le plus important)
    'soft_skills': 0.10,  # 10% pour les compétences comportementales
    'experience': 0.20,   # 20% pour l'expérience professionnelle
    'degree': 0.15,       # 15% pour la formation
    'salary': 0.025,      # 2.5% pour le salaire
    'remote_work': 0.025, # 2.5% pour la possibilité de télétravail
    'languages': 0.10     # 10% pour les compétences linguistiques
}

# Champs qui ne doivent pas être redistribués si d'autres sont manquants
FIXED_FIELDS = {'salary', 'remote_work'}

# Niveaux de compétence linguistique et leurs valeurs numériques
LANGUAGE_LEVELS = {
    "aucun": 0,
    "rien": 0,
    "débutant": 1,
    "basique": 1,
    "intermédiaire": 2,
    "moyen": 2,
    "avancé": 3,
    "courant": 3,
    "bilingue": 4, 
    "maternelle": 4,
    "bilingue/maternelle": 4,
    "natif": 4
}

# Niveaux de diplôme et leur équivalence numérique
DEGREE_LEVELS = {
    "bac+1": 1,
    "licence 1": 1,
    "bac+2": 2,
    "dut": 2,
    "bts": 2,
    "licence 2": 2,
    "licence": 3,
    "licence 3": 3,
    "bachelor": 3,
    "bac+3": 3,
    "bba": 4,
    "master 1": 4,
    "mastère 1": 4,
    "mastère spécialisé": 4,
    "bac+4": 4,
    "master 2": 5,
    "master": 5,
    "mastère 2": 5,
    "msc": 5,
    "diplôme d'ingénieur": 5,
    "ingénieur": 5,
    "mba": 5,
    "doctorat": 6,
    "phd": 6
}

# Correspondances entre abréviations et termes complets pour les diplômes
DIPLOMA_ABBREVIATIONS = {
    "IA": "Intelligence Artificielle",
    "AI": "Intelligence Artificielle",
    "CS": "Computer Science",
    "SWE": "Software Engineering",
    "IT": "Information Technology",
}

# Base de connaissances des relations entre compétences techniques
# Réduit les appels API en définissant à l'avance les relations entre technologies
TECH_SKILLS_RELATIONS = {
    # Langages de programmation et technologies associées
    "javascript": ["js", "es6", "ecmascript", "typescript", "angular", "react", "vue", "node.js", "jquery"],
    "typescript": ["ts", "javascript", "angular", "react"],
    "python": ["django", "flask", "fastapi", "numpy", "pandas", "scipy", "tensorflow", "pytorch", "scikit-learn", "machine learning"],
    "java": ["spring", "hibernate", "j2ee", "kotlin", "scala", "android"],
    "c#": ["dotnet", ".net", "asp.net", "entity framework", "xamarin", "unity"],
    "c++": ["c", "stl", "boost", "qt", "unreal engine"],
    "php": ["laravel", "symfony", "wordpress", "drupal", "magento"],
    "ruby": ["ruby on rails", "sinatra", "rspec"],
    "swift": ["ios", "cocoa", "objective-c", "xcode"],
    "go": ["golang", "gin", "echo"],
    "rust": ["cargo", "actix", "tokio"],
    
    # Technologies web
    "html": ["html5", "css", "web development", "front-end", "frontend"],
    "css": ["scss", "sass", "less", "bootstrap", "tailwind", "styled components", "html"],
    "react": ["react.js", "reactjs", "jsx", "redux", "react native", "javascript", "typescript"],
    "angular": ["angularjs", "typescript", "javascript"],
    "vue": ["vuejs", "vue.js", "nuxt", "javascript"],
    
    # Bases de données
    "sql": ["mysql", "postgresql", "oracle", "ms sql", "sqlite", "database", "db"],
    "nosql": ["mongodb", "couchdb", "firebase", "dynamodb", "database", "db"],
    "mongodb": ["mongo", "nosql", "database", "db"],
    "postgresql": ["postgres", "sql", "database", "db"],
    
    # Cloud & DevOps
    "aws": ["amazon web services", "ec2", "s3", "lambda", "cloud"],
    "azure": ["microsoft azure", "cloud"],
    "gcp": ["google cloud platform", "cloud"],
    "docker": ["container", "kubernetes", "k8s", "devops"],
    "kubernetes": ["k8s", "container orchestration", "docker", "devops"],
    "ci/cd": ["continuous integration", "continuous deployment", "jenkins", "github actions", "gitlab ci", "devops"],
    
    # Data Science
    "machine learning": ["ml", "ai", "artificial intelligence", "data science", "deep learning", "neural networks"],
    "data science": ["machine learning", "statistics", "data analysis", "big data", "python", "r"],
    "tensorflow": ["keras", "deep learning", "machine learning", "python"],
    "pytorch": ["deep learning", "machine learning", "python"],
    
    # Développement mobile
    "android": ["kotlin", "java", "mobile development"],
    "ios": ["swift", "objective-c", "mobile development"],
    "react native": ["react", "mobile development", "javascript", "typescript"],
    "flutter": ["dart", "mobile development"],
    
    # Gestion de version
    "git": ["github", "gitlab", "bitbucket", "version control"],
    
    # Divers
    "agile": ["scrum", "kanban", "jira", "project management"],
    "rest api": ["api", "restful", "web services"],
    "graphql": ["api", "apollo"],
}