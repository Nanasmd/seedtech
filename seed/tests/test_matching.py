# Test Matching Logic

import pytest
from app.matching import match_candidate_to_job
from app.models import Candidate, Job

def test_match_candidate_to_job():
    candidate = Candidate(
        id="1",
        name="John Doe",
        experiences=[],
        hard_skills=["Python", "Django"],
        soft_skills=["Communication", "Leadership"],
        degree="Master",
        languages={"fr": "courant", "en": "bilingue"},
        min_salary=45000,
        wants_remote=True
    )

    job = Job(
        title="Développeur Python",
        required_experiences=[],
        hard_skills=["Python", "Django", "SQL"],
        soft_skills=["Collaboration"],
        degree="Master",
        languages={"en": {"level": "bilingue", "required": True}},
        salary=50000,
        offers_remote=True
    )

    result = match_candidate_to_job(candidate, job)
    assert "candidate_id" in result
    assert "score" in result
    assert result["score"] > 0  # Vérifie qu'un score est bien calculé
