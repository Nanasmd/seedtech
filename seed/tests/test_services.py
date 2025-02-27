# Test Services OpenAI, Redis, Email

import pytest
import redis
from app.services import get_embeddings, send_email
from config.settings import config

def test_redis_connection():
    redis_client = redis.from_url(config.REDIS_URL)
    assert redis_client.ping() == True  # Vérifie que Redis répond

def test_get_embeddings():
    text = "Python"
    embedding = get_embeddings(text)
    assert isinstance(embedding, list)  # Vérifie qu'on obtient bien une liste de valeurs

def test_send_email(mocker):
    mocker.patch("smtplib.SMTP")  # Mock SMTP pour éviter l'envoi réel
    send_email("test@example.com", "Test", "Ceci est un test", "tests/dummy.json")
    assert True  # Si aucune erreur, c'est validé
