# Complete Setup Guide for the Matching System

This guide will walk you through setting up and running the candidate-job matching system on a computer where it has never been installed before.

## 1. Prerequisites

Ensure you have the following prerequisites installed:

- **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)
- **pip** (Python package manager) - Usually included with Python
- **Git** - Download from [git-scm.com](https://git-scm.com/downloads)

## 2. Clone the Repository

```bash
# Create a folder for your project
mkdir matching-system
cd matching-system

# Clone the repository (replace with actual repo URL)
git clone https://github.com/yourorganization/matching-system.git .
```

## 3. Set Up a Virtual Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

## 4. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

Key dependencies include:
- Flask
- OpenAI
- Redis (optional)
- NumPy
- Pydantic
- SQLAlchemy (optional for advanced DB features)

## 5. Set Up Environment Variables

Create a `.env` file in the project root:

```
# API Keys
OPENAI_API_KEY=your_openai_api_key_here

# Configuration
ENVIRONMENT=development
DEBUG=true
ENABLE_REDIS_CACHE=false
ANONYMIZE_DATA=true

# Performance
WORKER_THREADS=4
BATCH_SIZE=10
API_RATE_LIMIT=10

# Optional - Redis (if you want to use it)
# REDIS_URL=redis://localhost:6379/0
```

## 6. Initialize the System

Run the initialization script to create required folders and initial caches:

```bash
python -m src.initialize
```

This will create:
- `cache/` directory for local caching
- `outputs/` directory for result files
- Initial empty cache files

## 7. Start the Server

```bash
# Start the development server
python -m src.main
```

You should see output like:
```
Starting MatchingSystem v2.0.0
Environment: development
 * Running on http://0.0.0.0:8080
```

## 8. Using the System

### Basic Usage - Web Interface

1. Open a web browser and go to: `http://localhost:8080`
2. You'll see the API documentation and can test endpoints

### Basic Usage - API

#### Score a Single Candidate

```bash
curl -X POST http://localhost:8080/api/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "candidate": {
      "name": "John Doe",
      "experiences": [
        {"name": "Full Stack Developer", "months": 12}
      ],
      "hard_skills": ["JavaScript", "React", "Node.js"],
      "soft_skills": ["Communication", "Teamwork"],
      "degree_label": "Computer Science",
      "degree_level": "Master 1",
      "languages": {"anglais": "courant"},
      "min_salary": 40000,
      "wants_remote": true,
      "tags": ["Web Development", "JavaScript"]
    },
    "job": {
      "title": "Senior Developer",
      "required_experiences": [
        {"name": "Web Development", "months": 12, "category": "obligatoire"}
      ],
      "required_degree": "Master 1",
      "salary": 45000,
      "offers_remote": true,
      "hard_skills": [
        {"skill": "JavaScript", "category": "obligatoire"},
        {"skill": "React", "category": "recommandé"}
      ],
      "required_soft_skills": ["Communication", "Problem Solving"],
      "required_languages": {
        "anglais": {"level": "courant", "required": true}
      },
      "tags": ["Web Development", "JavaScript"]
    }
  }'
```

#### Process Multiple Candidates

```bash
curl -X POST http://localhost:8080/api/v1/batch \
  -H "Content-Type: application/json" \
  -d '{
    "candidates": [
      {
        "name": "John Doe",
        "experiences": [{"name": "Full Stack Developer", "months": 12}],
        "hard_skills": ["JavaScript", "React", "Node.js"],
        "tags": ["Web", "JavaScript"]
      },
      {
        "name": "Jane Smith",
        "experiences": [{"name": "Backend Developer", "months": 24}],
        "hard_skills": ["Python", "Django", "PostgreSQL"],
        "tags": ["Backend", "Python"]
      }
    ],
    "job": {
      "title": "Web Developer",
      "hard_skills": [{"skill": "JavaScript", "category": "obligatoire"}],
      "tags": ["Web", "JavaScript"]
    },
    "top_n": 1
  }'
```

## 9. Common Operations

### View Cache Statistics

```bash
curl http://localhost:8080/api/v1/cache/stats
```

### Download Results File

After running a batch job, you'll receive a filename. Download it with:

```bash
curl -O http://localhost:8080/api/v1/files/top_10_candidates_20250227_123456.json
```

### Check System Health

```bash
curl http://localhost:8080/health
```

## 10. Troubleshooting

### API Key Issues

If you see "OpenAI API error" messages, check that:
- Your API key is valid and has sufficient credits
- The `.env` file has the correct OPENAI_API_KEY value

### Performance Issues

If the system is slow:
- Consider enabling Redis (`ENABLE_REDIS_CACHE=true` in `.env`)
- Increase worker threads (`WORKER_THREADS=8` in `.env`)
- Check your internet connection speed

### Cache Problems

If you need to reset the cache:

```bash
curl -X POST http://localhost:8080/api/v1/cache/flush
```

## 11. Advanced Configuration

For production deployment, modify `.env`:

```
ENVIRONMENT=production
DEBUG=false
ENABLE_API_KEY_AUTH=true
API_KEY=your_secure_api_key
ENABLE_REDIS_CACHE=true
REDIS_URL=redis://your-redis-server:6379/0
```

## 12. Docker Deployment (Optional)

If you have Docker installed:

```bash
# Build the Docker image
docker build -t matching-system .

# Run the container
docker run -p 8080:8080 -e OPENAI_API_KEY=your_key_here matching-system
```

### 📌 **Comparaison entre l'ancien fichier `matching.py` et la nouvelle version dans le projet**

Après analyse approfondie, voici les **principales différences** entre la **première version de `matching.py`** et la **version actuelle dans le projet (`app/matching.py`)**.

---

## 🔍 **1. Changements structurels et organisationnels**
### ✅ **Ancienne Version (`matching.py` fourni)**
- **Plus structuré et modulaire** avec des classes bien définies pour :
  - La gestion de la configuration (`AppConfig`).
  - La gestion des modèles de données (candidats, emplois).
  - Les services et l'intégration API.
- **Implémente des techniques avancées** :
  - **Correspondance sémantique hybride IA** pour l’appariement candidat-emploi.
  - **Caching avec Redis** pour améliorer les performances.
  - **Traitement parallèle** pour accélérer les calculs.
- **Gestion robuste des erreurs et journalisation avancée (`logging`)**.

### 🆕 **Nouvelle Version (`app/matching.py`)**
- **Refactorisé pour une meilleure intégration avec l'architecture du projet**.
- **Séparation des responsabilités** :
  - `matching.py` ne gère plus directement la configuration, la journalisation ou les appels IA.
  - Ces éléments sont déportés vers `settings.py`, `redis_config.py` et `services.py`.
- **Meilleure maintenabilité** en utilisant `models.py` pour les objets candidats/emplois.

---

## 🚀 **2. Différences fonctionnelles**
| **Fonctionnalité** | **Ancienne Version (`matching.py`)** | **Nouvelle Version (`app/matching.py`)** |
|--------------------|---------------------------------|---------------------------------|
| **Gestion de la configuration** | `AppConfig` intégré dans `matching.py` | Géré dans `config/settings.py` |
| **Journalisation (`logging`)** | Configuré localement dans `matching.py` | Centralisé dans `settings.py` |
| **Caching** | Redis & fichier local (au choix) | Redis via `config/redis_config.py` |
| **Traitement par lot** | Traitement API OpenAI directement dans `matching.py` | Géré via `services.py` |
| **Sélection du modèle IA** | Définie dans `matching.py` | Configurable via `settings.py` |
| **Intégration API** | API Flask définie directement | API Flask déplacée vers `api.py` |
| **Correspondance candidat-emploi** | Calculs directement dans `matching.py` | Répartis entre `services.py` et `models.py` |

---

## 🛠 **3. Différences techniques majeures**
### **Ajouts et améliorations dans la nouvelle version :**
1. **Réorganisation des imports**  
   - Suppression des imports inutilisés.
   - Déplacement de la configuration et de la journalisation vers `config/`.
2. **Utilisation de `models.py`**  
   - Les classes `Candidate` et `Job` sont maintenant définies dans `models.py` et non plus dans `matching.py`.
3. **Délégation des interactions avec la base de données**  
   - `matching.py` ne gère plus directement les bases de données : tout passe par `services.py`.
4. **Gestion améliorée des appels IA**  
   - Avant : `matching.py` gérait directement les requêtes vers OpenAI.
   - Maintenant : `services.py` gère tous les appels IA (embeddings, similarités, GPT-4).
5. **Refonte du système de scoring**  
   - Avant : `calculate_match_score()` dans `matching.py` gérait tout.
   - Maintenant : Le score est calculé via plusieurs fonctions dans `services.py` pour plus de modularité.

---

## 🏆 **Conclusion**
La nouvelle version de `matching.py` est **plus robuste, évolutive et maintenable** :
✅ **Architecture modulaire** → Séparation entre la logique métier, les modèles et les services.  
✅ **Configuration flexible** → Tout est centralisé dans `settings.py` et `redis_config.py`.  
✅ **API mieux structurée** → `matching.py` ne contient plus d’API, elles sont gérées via `api.py`.  
✅ **Scalabilité améliorée** → Possibilité d’évoluer sans modifier le cœur du système.  

💡 **Prochaine étape ?** Si nécessaire, je peux fournir un **fichier diff détaillé** pour une comparaison ligne par ligne. 🚀📂

This setup guide should get you started with the matching system on any computer. The system is designed to be easy to install and use while providing powerful candidate-job matching capabilities.
