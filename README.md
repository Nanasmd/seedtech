# SEED Tech - Candidate Matching System

An AI-powered system for matching tech candidates with job openings, optimized for internships and apprenticeships.

## Features

- **Intelligent Matching**: Uses AI to calculate compatibility between candidates and tech job openings
- **Optimized Matching**: Compares hard skills, soft skills, experience, education, languages, and more
- **Reduced API Calls**: Implements caching and predefined relationships to minimize OpenAI API usage
- **Special Focus on Tech Skills**: Accurately identifies similarities between related technologies (e.g., TypeScript and JavaScript)
- **Workable Integration**: Seamlessly works with Workable ATS to fetch candidates and job data
- **GDPR Compliance**: Ensures proper handling of personal data
- **Parallel Processing**: Utilizes parallel execution for faster matching and response times

## Getting Started

### Prerequisites

- Python 3.9 or higher
- A Workable account with API access
- An OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/seed-tech-matching.git
   cd seed-tech-matching
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create an environment file:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your API keys and configuration settings.

### Running the application

For development:
```bash
python -m api.index
```

For production using waitress:
```bash
python -m waitress --port=8080 api.index:app
```

## API Endpoints

### Base Endpoints

- `GET /`: Home route, returns API info
- `GET /test`: Test route with sample data
- `GET /cache/stats`: Get cache statistics

### Scoring

- `POST /score`: Calculate match score between candidate and job

### Workable Integration

- `GET /workable/jobs`: Get all jobs from Workable
- `GET /workable/candidates`: Get all candidates from Workable
- `GET /workable/jobs/<job_shortcode>`: Get job details
- `GET /workable/candidates/<candidate_id>`: Get candidate details
- `GET /workable/jobs/<job_shortcode>/candidates`: Get candidates for a specific job

### Matching

- `GET /match/job/<job_shortcode>`: Match a job with all its candidates
- `GET /match?job_shortcode=<job_shortcode>&candidate_id=<candidate_id>`: Match a specific candidate with a specific job
- `POST /export/top_matches/<job_shortcode>`: Export top matches for a job

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `WORKABLE_API_KEY` | Workable API key | Required |
| `CACHE_DIR` | Directory for cache files | `cache` |
| `MAX_CACHE_SIZE` | Maximum number of entries in each cache | `10000` |
| `SIMILARITY_THRESHOLD` | Threshold for considering skills similar | `0.8` |
| `API_CALL_DELAY` | Delay between API calls (seconds) | `0.2` |
| `DEFAULT_MODEL` | Default OpenAI model to use | `gpt-4o-mini` |
| `DEBUG_MODE` | Enable debug logging | `False` |
| `PORT` | Port for the server | `8080` |
| `ENV` | Environment (development/production) | `development` |

## Deployment

This application is designed to be deployed to Vercel. The `vercel.json` configuration is included in the repository.

To deploy to Vercel:

1. Install the Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy the application:
   ```bash
   vercel
   ```

3. Set up environment variables in the Vercel dashboard.

## GDPR Compliance

This system is designed to be GDPR compliant:

- Personal data