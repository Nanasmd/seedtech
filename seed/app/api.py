# API Endpoints

from fastapi import FastAPI
from app.models import Candidate, Job
from app.matching import match_candidate_to_job

app = FastAPI()

@app.post("/match")
async def match_candidates(candidates: list[Candidate], job: Job):
    results = sorted(
        [match_candidate_to_job(candidate, job) for candidate in candidates],
        key=lambda x: x["score"],
        reverse=True
    )[:10]

    return {"top_candidates": results}
