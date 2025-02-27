import logging
from fastapi import FastAPI
from .routes import router
from .services.matching_service import MatchingService
from .services.openai_service import OpenAIService
from .services.cache_service import CacheService
from .config.settings import config

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MatchingSystem")
logger.info("Démarrage de l'application Matching System")

# Initialisation des services
cache_service = CacheService(config)
openai_service = OpenAIService(config, cache_service)
matching_service = MatchingService(config, openai_service, cache_service)

# Création de l'application FastAPI
app = FastAPI(
    title="Matching System API",
    description="API de matching candidats - entreprises",
    version="1.0.0"
)

# Enregistrement des routes
app.include_router(router)

@app.get("/")
async def home():
    return {"status": "running", "message": "Bienvenue sur l'API de matching"}

# Exposer les services en import direct
__all__ = ["app", "matching_service", "openai_service", "cache_service"]
