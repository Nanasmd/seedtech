# Configuration and Environment Variables

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    CACHE_TTL = int(os.getenv("CACHE_TTL", 86400))  # 24 heures
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

config = Config()

