"""
SEED Tech - Candidate Matching System
Parsing functions for converting Workable data to internal format
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
from typing import Dict, Any, List

from api.config import DEBUG_MODE

def calculate_months(start_date, end_date=None):
    """Calculate the number of months between two dates."""
    if not start_date:
        return 0

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.today()

        diff = relativedelta(end, start)
        return diff.years * 12 + diff.months
    except ValueError:
        # If date parsing fails, return a default value
        if DEBUG_MODE:
            print(f"Error parsing dates: {start_date} - {end_date}")
        return 0

def extract_text(html_content):
    """Extract plain text from HTML content."""
    if not html_content:
        return ""

    try:
        return BeautifulSoup(html_content, "html.parser").get_text("\n-")
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error extracting text from HTML: {e}")
        return html_content

def extract_soft_skills(text: str) -> List[str]:
    """Extract potential soft skills from text.

    This is a simple implementation that looks for common soft skill keywords.
    A more sophisticated approach could use NLP techniques or AI.
    """
    if not text:
        return []

    # List of common soft skills to look for
    common_soft_skills = [
        "communication", "teamwork", "travail d'équipe", "leadership", 
        "problem solving", "résolution de problèmes", "creativity", "créativité",
        "adaptability", "adaptabilité", "time management", "gestion du temps",
        "critical thinking", "organisation", "collaboration", "autonomie", "autonomy",
        "attention to detail", "attention aux détails", "flexibility", "flexibilité",
        "interpersonal", "interpersonnel", "motivation", "persuasion", "negotiation", "négociation"
    ]

    # Normalize text
    normalized_text = text.lower()

    # Find matches
    found_skills = []
    for skill in common_soft_skills:
        if skill in normalized_text:
            found_skills.append(skill)

    return found_skills

def parse_workable_candidate(candidate_data) -> Dict[str, Any]:
    """Parse candidate data from Workable API into our internal format."""
    if not candidate_data:
        return {}
        
    experiences = []
    
    # Parse professional experiences
    for exp in candidate_data.get("experience_entries", []):
        experiences.append({
            "name": exp.get("title", ""),
            "months": calculate_months(exp.get("start_date"), exp.get("end_date")),
            "description": extract_text(exp.get("summary", ""))
        })
    
    # Parse education entries
    education = candidate_data.get("education_entries", [])
    degree = education[0].get("degree", "") if education else ""
    
    # Parse skills
    hard_skills = [skill.get("name", "") for skill in candidate_data.get("skills", [])]
    
    # Extract potential soft skills from resume summary and experience descriptions
    soft_skills = []
    summary = extract_text(candidate_data.get("summary", ""))
    if summary:
        soft_skills.extend(extract_soft_skills(summary))
    
    for exp in candidate_data.get("experience_entries", []):
        exp_description = extract_text(exp.get("summary", ""))
        if exp_description:
            soft_skills.extend(extract_soft_skills(exp_description))
    
    # Remove duplicates and limit to a reasonable number
    soft_skills = list(set(soft_skills))[:10]
    
    # Parse languages
    languages = {}
    for lang in candidate_data.get("languages", []):
        lang_name = lang.get("name", "").lower()
        proficiency = lang.get("proficiency", "").lower()
        if lang_name and proficiency:
            languages[lang_name] = proficiency
    
    # Extract tags from keywords, skills, and job titles
    tags = []
    # Add explicit tags if available
    if candidate_data.get("tags"):
        tags.extend([tag.lower() for tag in candidate_data.get("tags", [])])
    
    # Add skill names as tags
    for skill in hard_skills:
        if skill:
            tags.append(skill.lower())
    
    # Add job titles from experiences as tags
    for exp in experiences:
        title = exp.get("name", "").lower()
        if title:
            # Try to extract key terms from titles
            title_words = title.split()
            for word in title_words:
                if len(word) > 3 and word not in ["and", "with", "pour", "avec", "dans", "chez"]:
                    tags.append(word)
    
    # Remove duplicates and limit to a reasonable number
    tags = list(set(tags))[:20]
    
    # Build candidate object
    candidate = {
        "name": f"{candidate_data.get('candidate', {}).get('firstname', '')} {candidate_data.get('candidate', {}).get('lastname', '')}",
        "experiences": experiences,
        "degree": degree,
        "wants_remote": candidate_data.get("location", {}).get("telecommuting", False),
        "min_salary": candidate_data.get("salary", {}).get("salary_from", 1100),
        "hard_skills": hard_skills,
        "soft_skills": soft_skills,
        "tags": tags,
        "languages": languages
    }
    
    return candidate

def parse_workable_job(job_data) -> Dict[str, Any]:
    """Parse job data from Workable API into our internal format."""
    if not job_data:
        return {}
    
    # Extract requirements as experiences
    requirements_text = extract_text(job_data.get("requirements", ""))
    requirements_list = [req.strip() for req in requirements_text.split("\n-") if req.strip()]
    
    required_experiences = []
    for i, req in enumerate(requirements_list):
        if len(req) > 10:  # Only include substantial requirements
            required_experiences.append({
                "name": req[:50] + "..." if len(req) > 50 else req,
                "months": 12,  # Default to 1 year
                "description": req,
                "category": "obligatoire" if i < 3 else "recommandée"  # First 3 are obligatory
            })
    
    # Extract hard skills from requirements and also from the benefits section
    hard_skills = []
    
    # From requirements
    for i, req in enumerate(requirements_list):
        if len(req) > 5:
            hard_skills.append({
                "skill": req[:50] + "..." if len(req) > 50 else req,
                "category": "obligatoire" if i < 3 else "recommandé"
            })
    
    # Extract from description for additional skills
    description_text = extract_text(job_data.get("description", ""))
    
    # Look for tech keywords in the description
    tech_keywords = [
        "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Ruby", "PHP", "Swift", "Kotlin",
        "React", "Angular", "Vue", "Node.js", "Django", "Flask", "Spring", "ASP.NET", 
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD", "DevOps",
        "SQL", "MongoDB", "PostgreSQL", "MySQL", "NoSQL", "Redis",
        "Machine Learning", "AI", "Data Science", "Big Data", "Analytics",
        "Git", "Agile", "Scrum", "REST API", "GraphQL"
    ]
    
    for keyword in tech_keywords:
        if keyword.lower() in description_text.lower() and not any(skill["skill"].lower() == keyword.lower() for skill in hard_skills):
            hard_skills.append({
                "skill": keyword,
                "category": "recommandé"
            })
    
    # Extract soft skills
    soft_skills = extract_soft_skills(description_text + " " + requirements_text)
    
    # Extract languages from requirements
    languages = {}
    language_keywords = ["anglais", "english", "français", "french", "espagnol", "spanish", "allemand", "german"]
    
    for lang in language_keywords:
        if lang in requirements_text.lower():
            # Try to determine if it's required and the level
            context = requirements_text.lower().split(lang)[1][:50] if lang in requirements_text.lower() else ""
            is_required = "obligatoire" in context or "requis" in context or "required" in context
            
            level = "intermédiaire"  # Default level
            if "courant" in context or "fluent" in context:
                level = "courant"
            elif "bilingue" in context or "bilingual" in context or "native" in context or "maternelle" in context:
                level = "bilingue/maternelle"
            elif "débutant" in context or "basic" in context or "notions" in context:
                level = "débutant"
            
            # Map to standard language names
            std_lang = lang
            if lang in ["anglais", "english"]:
                std_lang = "anglais"
            elif lang in ["français", "french"]:
                std_lang = "français"
            elif lang in ["espagnol", "spanish"]:
                std_lang = "espagnol"
            elif lang in ["allemand", "german"]:
                std_lang = "allemand"
            
            languages[std_lang] = {
                "level": level,
                "required": is_required
            }
    
    # Extract tags
    tags = []
    # Add explicit tags if available
    if job_data.get("tags"):
        tags.extend([tag.lower() for tag in job_data.get("tags", [])])
    
    # Add keywords if available
    if job_data.get("keywords"):
        tags.extend([keyword.lower() for keyword in job_data.get("keywords", [])])
    
    # Add skill names as tags
    for skill in hard_skills:
        if skill.get("skill"):
            tags.append(skill["skill"].lower())
    
    # Remove duplicates and limit
    tags = list(set(tags))[:20]
    
    # Determine remote work status
    offers_remote = False
    if job_data.get("location", {}).get("telecommuting"):
        offers_remote = True
    elif "remote" in description_text.lower() or "télétravail" in description_text.lower():
        offers_remote = True
    
    # Build job object
    job = {
        "title": job_data.get("title", ""),
        "required_experiences": required_experiences,
        "required_degree": job_data.get("education", ""),
        "offers_remote": offers_remote,
        "salary": job_data.get("salary", {}).get("salary_from", 1200),
        "hard_skills": hard_skills,
        "required_soft_skills": soft_skills,
        "tags": tags,
        "required_languages": languages
    }
    
    return job