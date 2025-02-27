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

This setup guide should get you started with the matching system on any computer. The system is designed to be easy to install and use while providing powerful candidate-job matching capabilities.