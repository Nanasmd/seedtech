# Data Models

from pydantic import BaseModel
from typing import List, Dict, Optional

class Candidate(BaseModel):
    id: str
    name: str
    experiences: List[Dict]
    hard_skills: List[str]
    soft_skills: List[str]
    degree: str
    languages: Dict[str, str]
    min_salary: Optional[float]
    wants_remote: bool

class Job(BaseModel):
    title: str
    required_experiences: List[Dict]
    hard_skills: List[str]
    soft_skills: List[str]
    degree: str
    languages: Dict[str, str]
    salary: Optional[float]
    offers_remote: bool
