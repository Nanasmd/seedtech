# Documentation Complète du Projet SEED Tech Matching System

## Introduction

Le SEED Tech Matching System est une solution innovante développée pour faciliter la mise en relation entre les étudiants en technologie et les entreprises cherchant à recruter pour des stages, alternances et autres opportunités. Grâce à l'intelligence artificielle, ce système analyse et calcule la compatibilité entre les profils des candidats et les offres d'emploi, en se concentrant particulièrement sur les compétences techniques (hard skills), l'expérience professionnelle, la formation académique, et d'autres critères pertinents.

Cette documentation est destinée au CTO et unique développeur full stack du projet, et vise à fournir une compréhension approfondie de l'architecture, des fonctionnalités et de l'implémentation technique du système.

## Structure du Projet

```
seed-tech-matching/
│
├── api/
│   ├── index.py                # Point d'entrée principal de l'API
│   ├── config.py               # Configuration du système
│   ├── database.py             # Gestion de la base de données
│   ├── similarity.py           # Calcul de similarité
│   ├── scoring.py              # Algorithmes de scoring
│   ├── parsing.py              # Fonctions d'analyse des données
│   └── workable.py             # Intégration avec l'API Workable
│
├── db/                         # Répertoire de la base de données
│   └── seed_tech.db            # Fichier SQLite (créé au premier lancement)
│
├── .env                        # Variables d'environnement (non versionné)
├── .env.example                # Exemple de variables d'environnement
├── .gitignore                  # Configuration Git
├── requirements.txt            # Dépendances Python
├── vercel.json                 # Configuration pour déploiement Vercel
└── README.md                   # Documentation générale
```

## Description Détaillée des Fichiers

### 1. api/index.py

**Rôle** : Point d'entrée principal de l'API, gestion des routes HTTP.

**Fonctionnalités clés** :
- Initialisation de l'application Flask
- Configuration du CORS (Cross-Origin Resource Sharing)
- Définition des routes API
- Gestion des requêtes entrantes
- Acheminement des demandes vers les modules appropriés

**Pour non-techniciens** : Ce fichier est comparable à l'accueil d'un bâtiment. Il reçoit toutes les demandes des utilisateurs, les analyse, et les dirige vers le bon service (module) qui pourra y répondre. C'est également lui qui s'assure que seules les demandes légitimes sont traitées.

### 2. api/config.py

**Rôle** : Centralisation de tous les paramètres de configuration.

**Fonctionnalités clés** :
- Chargement des variables d'environnement
- Configuration des clés API (OpenAI, Workable)
- Paramètres de base de données (SQLite, Redis)
- Définition des constantes du système
- Configuration des poids pour l'algorithme de matching

**Pour non-techniciens** : Imaginez ce fichier comme le tableau de bord d'une voiture. Il contient tous les réglages qui déterminent comment le système va fonctionner. Plutôt que d'avoir ces paramètres dispersés dans différents fichiers, ils sont tous regroupés ici pour faciliter les ajustements.

### 3. api/database.py

**Rôle** : Gestion de la persistance des données et du cache.

**Fonctionnalités clés** :
- Connexion à SQLite pour le stockage permanent
- Connexion à Redis pour le cache rapide en mémoire
- Fonctions pour sauvegarder/récupérer les scores de similarité
- Stockage des résultats de matching
- Statistiques sur l'utilisation du cache

**Pour non-techniciens** : Ce module est comparable à un système de classement très élaboré. Il permet de stocker les informations de manière organisée (base de données SQLite) et de garder les informations les plus fréquemment consultées à portée de main (cache Redis). C'est grâce à lui que le système n'a pas besoin de recalculer des informations déjà connues.

### 4. api/similarity.py

**Rôle** : Calcul de la similarité entre différents éléments textuels.

**Fonctionnalités clés** :
- Normalisation du texte (mise en minuscules, suppression de ponctuation)
- Calcul de similarité entre compétences techniques via OpenAI
- Base de connaissances intégrée sur les relations entre technologies
- Mise en cache des résultats de similarité

**Pour non-techniciens** : Ce module est l'expert linguistique du système. Il est capable de déterminer à quel point deux termes sont similaires, par exemple s'il y a une relation entre "JavaScript" et "TypeScript", ou si "Développeur Full Stack" et "Ingénieur Web" désignent des rôles proches. Il utilise l'IA d'OpenAI pour les cas complexes, mais dispose aussi d'une "mémoire" des associations courantes pour éviter de solliciter l'IA à chaque fois.

### 5. api/scoring.py

**Rôle** : Algorithmes de calcul des scores de compatibilité.

**Fonctionnalités clés** :
- Calcul des scores pour chaque dimension (compétences, expérience, etc.)
- Pondération adaptative des différentes dimensions
- Traitement parallèle pour optimiser les performances
- Stockage des résultats de matching dans la base de données

**Pour non-techniciens** : C'est le "cerveau" analytique du système. Il évalue la compatibilité entre un candidat et une offre selon plusieurs critères, puis combine ces évaluations en un score global. C'est comme un jury d'experts qui noterait différents aspects d'une candidature, mais de façon automatisée et objective.

### 6. api/parsing.py

**Rôle** : Analyse et transformation des données externes.

**Fonctionnalités clés** :
- Extraction de texte à partir du HTML
- Calcul des durées d'expérience
- Extraction des compétences douces (soft skills)
- Conversion des données Workable en format interne

**Pour non-techniciens** : Ce module est le "traducteur" du système. Il convertit les données provenant de l'extérieur (comme Workable) dans un format que notre système peut comprendre et traiter. C'est comme si vous receviez des documents dans différentes langues et formats, et que ce module les traduisait tous dans un format standardisé.

### 7. api/workable.py

**Rôle** : Interface avec l'API de Workable.

**Fonctionnalités clés** :
- Communication avec l'API Workable
- Récupération des offres d'emploi et des candidats
- Mise en correspondance des candidats avec les offres
- Export des résultats de matching

**Pour non-techniciens** : Ce module est l'interface entre notre système et Workable (le logiciel de recrutement). Il sait comment "parler" à Workable pour récupérer les informations sur les offres et les candidats, et comment lui renvoyer nos résultats d'analyse.

## Base de Données et Cache

Le système utilise une architecture de cache à deux niveaux :

### SQLite (Base de données principale)
- Stockage persistant des données
- Tables pour les caches de similarité
- Table pour les résultats de matching
- Indices pour optimiser les recherches

### Redis (Cache en mémoire)
- Cache ultra-rapide pour les scores de similarité
- Expiration automatique des entrées
- Fallback sur SQLite si Redis n'est pas disponible

**Pour non-techniciens** : Imaginez SQLite comme une bibliothèque bien organisée avec tous les livres (données) rangés méthodiquement. Redis serait comme un petit bureau à côté de cette bibliothèque, où l'on garde les livres consultés récemment pour y accéder encore plus rapidement. Si quelqu'un demande un livre qui n'est pas sur le bureau, on va le chercher dans la bibliothèque, puis on le garde sur le bureau pour la prochaine fois.

## Algorithme de Matching

L'algorithme de matching évalue la compatibilité entre un candidat et une offre selon plusieurs dimensions :

1. **Compétences techniques (hard skills)** : Correspondance entre les compétences requises et celles du candidat
2. **Expérience professionnelle** : Similitude des postes occupés et durée d'expérience
3. **Formation** : Niveau d'étude et domaine de spécialisation
4. **Langues** : Niveau dans les langues requises
5. **Compétences comportementales (soft skills)** : Correspondance entre qualités personnelles
6. **Critères additionnels** : Salaire, télétravail, etc.

Ces dimensions sont pondérées de manière adaptative selon les informations disponibles. Si certaines informations sont manquantes, les poids sont redistribués proportionnellement.

**Pour non-techniciens** : L'algorithme fonctionne comme un recruteur virtuel qui évaluerait méthodiquement chaque aspect d'une candidature par rapport aux exigences du poste. Il attribue des notes pour chaque critère, puis calcule une note globale en donnant plus d'importance à certains critères qu'à d'autres (par exemple, les compétences techniques comptent généralement plus que les préférences de télétravail).

## Optimisations pour Réduire les Appels API

Le système intègre plusieurs optimisations pour minimiser les appels à l'API OpenAI (qui sont coûteux) :

1. **Système de cache à deux niveaux** : Redis pour la vitesse, SQLite pour la persistance
2. **Base de connaissances intégrée** : Relations prédéfinies entre technologies (ex: JavaScript/TypeScript)
3. **Réutilisation des résultats** : Les matchs récents sont réutilisés plutôt que recalculés
4. **Traitement parallèle** : Calcul simultané des différentes dimensions du matching

**Pour non-techniciens** : Ces optimisations sont comparables à un système qui, avant de poser une question à un expert externe (OpenAI), vérifie d'abord s'il connaît déjà la réponse ou s'il peut la déduire avec ses propres connaissances. Cela permet d'économiser du temps et des ressources.

## Configuration et Déploiement

### Variables d'Environnement (.env)

```
# Clés API
OPENAI_API_KEY=votre_clé_openai_ici
WORKABLE_API_KEY=votre_clé_workable_ici

# Configuration de la base de données
DATABASE_URL=db/seed_tech.db
REDIS_URL=redis://localhost:6379/0
CACHE_EXPIRY_SECONDS=604800  # 1 semaine en secondes
MAX_CACHE_ENTRIES=100000

# Configuration du matching
SIMILARITY_THRESHOLD=0.8
API_CALL_DELAY=0.2

# Configuration OpenAI
DEFAULT_MODEL=gpt-4o-mini

# Configuration de l'application
DEBUG_MODE=False
PORT=8080
ENV=development
```

### Déploiement sur Vercel

Le fichier `vercel.json` configure le déploiement sur la plateforme Vercel :

```json
{
  "functions": {
    "api/**/*": {
      "maxDuration": 60
    }
  },
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/index"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Access-Control-Allow-Origin",
          "value": "*"
        },
        {
          "key": "Access-Control-Allow-Methods",
          "value": "GET, POST, OPTIONS"
        },
        {
          "key": "Access-Control-Allow-Headers",
          "value": "Content-Type, Authorization"
        }
      ]
    }
  ],
  "env": {
    "OPENAI_API_KEY": "@openai_api_key",
    "WORKABLE_API_KEY": "@workable_api_key",
    "DEBUG_MODE": "false",
    "CACHE_DIR": "/tmp/cache",
    "DEFAULT_MODEL": "gpt-4o-mini"
  }
}
```

**Pour non-techniciens** : Ce fichier indique à la plateforme Vercel comment déployer notre application. Il définit notamment les limites de temps d'exécution, comment router les requêtes, et quelles variables d'environnement utiliser.

## Utilisation de l'API

### Routes Principales

1. **`GET /`** : Page d'accueil, retourne les informations sur l'API
2. **`GET /test`** : Route de test avec des données d'exemple
3. **`POST /score`** : Calcule le score de matching entre un candidat et une offre

### Routes d'Intégration Workable

1. **`GET /workable/jobs`** : Récupère toutes les offres d'emploi de Workable
2. **`GET /workable/candidates`** : Récupère tous les candidats de Workable
3. **`GET /workable/jobs/<job_shortcode>`** : Récupère les détails d'une offre
4. **`GET /workable/candidates/<candidate_id>`** : Récupère les détails d'un candidat
5. **`GET /match/job/<job_shortcode>`** : Match une offre avec tous ses candidats
6. **`GET /match?job_shortcode=X&candidate_id=Y`** : Match un candidat spécifique avec une offre
7. **`POST /export/top_matches/<job_shortcode>`** : Exporte les meilleurs matchs pour une offre

**Pour non-techniciens** : Ces routes sont les différentes "portes d'entrée" de notre API. Chacune permet d'accéder à une fonctionnalité spécifique, comme récupérer des informations sur les offres d'emploi, ou calculer la compatibilité entre un candidat et un poste.

## Conformité RGPD

Le système est conçu avec la conformité RGPD à l'esprit :

1. **Minimisation des données** : Seules les données nécessaires sont traitées
2. **Limitation de conservation** : Expiration automatique des données en cache
3. **Sécurité** : En-têtes HTTP de sécurité, stockage sécurisé des clés API
4. **Transparence** : Documentation claire sur le fonctionnement de l'algorithme

**Pour non-techniciens** : Le système respecte les principes du RGPD en ne collectant que les données nécessaires, en les conservant pour une durée limitée, et en assurant leur sécurité. Il est également conçu pour être transparent sur son fonctionnement.

## Maintenance et Evolution

### Surveillance du Système

Pour surveiller le système en production :

1. **Utiliser l'endpoint `/cache/stats`** pour vérifier l'utilisation du cache
2. **Consulter les logs** pour détecter d'éventuelles erreurs
3. **Monitorer l'utilisation des API** OpenAI et Workable

### Évolutions Possibles

1. **Migration vers PostgreSQL** pour les déploiements à grande échelle
2. **Ajout d'une interface utilisateur** pour visualiser les matchs
3. **Intégration avec d'autres ATS** au-delà de Workable
4. **Amélioration de l'analyse des compétences** avec des techniques NLP plus avancées
5. **Système de feedback** pour améliorer l'algorithme de matching en fonction des retours

**Pour non-techniciens** : Comme tout système, celui-ci peut évoluer. Les suggestions ci-dessus sont des pistes d'amélioration, comme ajouter une interface graphique ou rendre le système compatible avec d'autres logiciels de recrutement.

## Conclusion

Le SEED Tech Matching System est une solution puissante et optimisée pour mettre en relation les candidats tech avec les entreprises qui recrutent. Son architecture modulaire, son système de cache intelligent et son intégration avec Workable en font un outil précieux pour identifier rapidement les candidats les plus compatibles avec chaque offre d'emploi.

La mise en place de la base de données améliore considérablement les performances et la scalabilité du système, le rendant prêt pour une utilisation en environnement de production avec un volume important de candidats et d'offres.
