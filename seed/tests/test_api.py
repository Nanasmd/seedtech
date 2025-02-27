# Test API

import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_match_endpoint():
    payload = {
        "candidates": [
            {
                "id": "1",
                "name": "John Doe",
                "experiences": [],
                "hard_skills": ["Python", "Django"],
                "soft_skills": ["Communication", "Leadership"],
                "degree": "Master",
                "languages": {"fr": "courant", "en": "bilingue"},
                "min_salary": 45000,
                "wants_remote": True
            }
        ],
        "job": {
            "title": "Développeur Python",
            "required_experiences": [],
            "hard_skills": ["Python", "Django", "SQL"],
            "soft_skills": ["Collaboration"],
            "degree": "Master",
            "languages": {"en": {"level": "bilingue", "required": True}},
            "salary": 50000,
            "offers_remote": True
        }
    }
    response = client.post("/match", json=payload)
    assert response.status_code == 200
    assert "top_candidates" in response.json()
