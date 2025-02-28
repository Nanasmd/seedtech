# Guide d'Installation et d'Utilisation du SEED Tech Matching System
*À destination des fondateurs non-techniques*

## Sommaire

1. [Introduction](#introduction)
2. [Prérequis](#prérequis)
3. [Installation sur votre ordinateur](#installation-sur-votre-ordinateur)
   - [Installation de Python](#1-installation-de-python)
   - [Téléchargement du projet](#2-téléchargement-du-projet)
   - [Installation des dépendances](#3-installation-des-dépendances)
   - [Configuration des clés API](#4-configuration-des-clés-api)
   - [Installation de Redis (optionnel)](#5-installation-de-redis-optionnel)
4. [Démarrage du système](#démarrage-du-système)
5. [Utilisation quotidienne](#utilisation-quotidienne)
   - [Trouver les meilleurs candidats pour une offre](#trouver-les-meilleurs-candidats-pour-une-offre)
   - [Évaluer un candidat spécifique](#évaluer-un-candidat-spécifique)
   - [Exporter les résultats](#exporter-les-résultats)
6. [Comprendre les scores](#comprendre-les-scores)
7. [Résolution des problèmes courants](#résolution-des-problèmes-courants)
8. [Questions fréquentes](#questions-fréquentes)

---

## Introduction

Le SEED Tech Matching System est une solution qui utilise l'intelligence artificielle pour mettre en relation les étudiants en technologie avec les entreprises tech. Ce guide vous expliquera, étape par étape, comment installer et utiliser ce système sur votre ordinateur, même si vous n'avez pas de compétences techniques.

---

## Prérequis

Avant de commencer, vous aurez besoin de :

- Un ordinateur sous Windows, macOS ou Linux
- Une connexion Internet
- Des clés API pour OpenAI et Workable (nous verrons comment les obtenir)
- Un compte Workable actif avec vos offres et candidats

---

## Installation sur votre ordinateur

### 1. Installation de Python

Python est le langage de programmation utilisé par notre système. Vous devez l'installer sur votre ordinateur.

#### Sous Windows

1. Visitez [python.org](https://www.python.org/downloads/)
2. Cliquez sur "Download Python 3.9" (ou version plus récente)
3. Lancez l'installateur téléchargé
4. **Important** : Cochez la case "Add Python to PATH" avant de cliquer sur "Install Now"
5. Suivez les instructions d'installation

#### Sous macOS

1. Installez Homebrew (si ce n'est pas déjà fait) en ouvrant Terminal et en exécutant :
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Installez Python avec Homebrew :
   ```
   brew install python
   ```

#### Vérifiez l'installation

Ouvrez un terminal (Invite de commandes sous Windows) et tapez :
```
python --version
```

Vous devriez voir quelque chose comme "Python 3.9.7" (le numéro de version peut varier).

### 2. Téléchargement du projet

1. Visitez la page GitHub du projet [SEED Tech Matching System](https://github.com/votre-organisation/seed-tech-matching)
2. Cliquez sur le bouton vert "Code"
3. Sélectionnez "Download ZIP"
4. Décompressez le fichier téléchargé dans un dossier de votre choix (par exemple, "Documents/SEED")

### 3. Installation des dépendances

Les dépendances sont des bibliothèques nécessaires au fonctionnement du système.

1. Ouvrez un terminal (Invite de commandes sous Windows)
2. Naviguez jusqu'au dossier où vous avez décompressé le projet :
   ```
   cd chemin/vers/votre/dossier/seed-tech-matching
   ```
3. Installez les dépendances requises :
   ```
   pip install -r requirements.txt
   ```

### 4. Configuration des clés API

#### Obtenir une clé OpenAI

1. Créez un compte sur [OpenAI](https://platform.openai.com/)
2. Naviguez vers "API Keys" dans votre compte
3. Cliquez sur "Create new secret key"
4. Copiez la clé (elle ne sera plus jamais affichée)

#### Obtenir une clé Workable

1. Connectez-vous à votre compte Workable
2. Allez dans Settings > Integrations > API
3. Générez ou copiez votre clé API existante

#### Configurer le fichier .env

1. Dans le dossier du projet, localisez le fichier `.env.example`
2. Faites-en une copie et renommez-la en `.env` (sans extension après le point)
3. Ouvrez ce fichier avec un éditeur de texte (comme Notepad, TextEdit ou Visual Studio Code)
4. Remplacez les valeurs par vos clés API :
   ```
   OPENAI_API_KEY=votre_clé_openai_ici
   WORKABLE_API_KEY=votre_clé_workable_ici
   ```
5. Sauvegardez le fichier

### 5. Installation de Redis (optionnel)

Redis est un système de cache qui accélère les performances, mais il est optionnel. Le système fonctionnera sans, mais sera plus rapide avec.

#### Sous Windows

1. Téléchargez [Redis pour Windows](https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi)
2. Exécutez l'installateur et suivez les instructions

#### Sous macOS

1. Installez Redis avec Homebrew :
   ```
   brew install redis
   ```
2. Démarrez Redis :
   ```
   brew services start redis
   ```

---

## Démarrage du système

Maintenant que tout est configuré, vous pouvez démarrer le système :

1. Ouvrez un terminal (Invite de commandes sous Windows)
2. Naviguez jusqu'au dossier du projet :
   ```
   cd chemin/vers/votre/dossier/seed-tech-matching
   ```
3. Démarrez le serveur :
   ```
   python -m api.index
   ```
4. Vous devriez voir un message indiquant que le serveur a démarré, généralement sur http://localhost:5000

Le système est maintenant opérationnel et prêt à être utilisé !

---

## Utilisation quotidienne

Vous pouvez interagir avec le système de plusieurs façons. Pour les non-techniciens, nous recommandons d'utiliser un outil comme [Postman](https://www.postman.com/downloads/) qui offre une interface graphique pour tester les API.

### Trouver les meilleurs candidats pour une offre

1. Dans Postman, créez une nouvelle requête GET
2. Entrez l'URL : `http://localhost:5000/match/job/JOB_SHORTCODE`
   (remplacez JOB_SHORTCODE par le code court de votre offre dans Workable)
3. Cliquez sur "Send"
4. Vous recevrez une liste des candidats les mieux classés pour cette offre

### Évaluer un candidat spécifique

1. Dans Postman, créez une nouvelle requête GET
2. Entrez l'URL : `http://localhost:5000/match?job_shortcode=JOB_SHORTCODE&candidate_id=CANDIDATE_ID`
   (remplacez les valeurs par vos identifiants réels)
3. Cliquez sur "Send"
4. Vous recevrez une analyse détaillée de la compatibilité entre ce candidat et cette offre

### Exporter les résultats

1. Dans Postman, créez une nouvelle requête POST
2. Entrez l'URL : `http://localhost:5000/export/top_matches/JOB_SHORTCODE`
3. Cliquez sur "Send"
4. Vous recevrez un résumé des meilleurs candidats que vous pourrez copier-coller

---

## Comprendre les scores

Le système évalue les candidats selon plusieurs dimensions :

- **Score global** : Note générale de compatibilité (0-1)
- **Compétences techniques** : Correspondance entre les compétences requises et celles du candidat
- **Expérience professionnelle** : Similitude des postes occupés et durée d'expérience
- **Formation** : Adéquation du niveau d'étude et du domaine
- **Langues** : Niveau dans les langues requises
- **Compétences comportementales** : Correspondance entre les soft skills

Plus le score est proche de 1, meilleure est la compatibilité.

---

## Résolution des problèmes courants

### "Le serveur ne démarre pas"

Vérifiez que :
- Python est correctement installé
- Vous êtes dans le bon dossier
- Toutes les dépendances sont installées
- Le fichier `.env` est correctement configuré

### "Je n'arrive pas à me connecter à Workable"

Vérifiez que :
- Votre clé API Workable est correcte
- Votre compte Workable est actif
- Vous avez les permissions nécessaires pour accéder à l'API

### "Les scores sont toujours à zéro"

Vérifiez que :
- Vos offres contiennent bien des compétences requises
- Les profils des candidats sont suffisamment détaillés
- Il y a des tags communs entre les offres et les candidats

---

## Questions fréquentes

### Combien coûte l'utilisation de l'API OpenAI ?

OpenAI facture en fonction du nombre de requêtes et de la quantité de texte traitée. Pour un usage modéré (quelques centaines de candidats par mois), comptez entre 10€ et 50€ mensuels.

### Les données sont-elles sécurisées ?

Oui, toutes les données restent sur votre ordinateur ou dans vos systèmes. Les seules informations envoyées à OpenAI sont des fragments anonymisés pour calculer les similarités.

### Puis-je utiliser ce système sans Workable ?

Le système est optimisé pour Workable, mais il est possible de l'adapter à d'autres ATS. Contactez votre développeur pour cette personnalisation.

### Comment améliorer la précision des matchs ?

- Assurez-vous que les offres contiennent des descriptions détaillées des compétences requises
- Encouragez les candidats à remplir leurs profils de manière exhaustive
- Utilisez des tags cohérents entre les offres et les profils candidats

---

Nous espérons que ce guide vous a aidé à installer et utiliser le SEED Tech Matching System. Si vous avez d'autres questions ou besoin d'assistance, n'hésitez pas à contacter votre équipe technique.

**Bon recrutement !**
