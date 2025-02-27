# Services (Redis, OpenAI, Email)

import pickle
import smtplib
from email.message import EmailMessage
from openai import OpenAI
from config.redis_config import redis_client
from config.settings import config

# Initialisation OpenAI
client = OpenAI(api_key=config.OPENAI_API_KEY)

# Fonction pour obtenir des embeddings OpenAI
def get_embeddings(text):
    cache_key = f"embedding:{text}"
    cached_embedding = redis_client.get(cache_key)

    if cached_embedding:
        return pickle.loads(cached_embedding)

    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    embedding = response.data[0].embedding

    redis_client.setex(cache_key, config.CACHE_TTL, pickle.dumps(embedding))
    return embedding

# Fonction d’envoi d’email avec fichier JSON en pièce jointe
def send_email(to_email, subject, body, attachment_path):
    msg = EmailMessage()
    msg["From"] = config.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with open(attachment_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="json", filename="top_candidates.json")

    with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)
