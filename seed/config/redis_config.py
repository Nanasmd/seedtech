# Redis Connection Setup

import redis
from config.settings import config

# Connexion à Redis
redis_client = redis.from_url(config.REDIS_URL)
