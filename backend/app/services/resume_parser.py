import re
import json
import logging
from typing import Dict, Any, List, Optional
from app.services.ai import AIProvider

logger = logging.getLogger("uvicorn.error")

# Standard Skill Normalization Map
NORMALIZATION_MAP = {
    "react.js": "React",
    "reactjs": "React",
    "react": "React",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "vue": "Vue.js",
    "python3": "Python",
    "python 3": "Python",
    "python": "Python",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "fastapi": "FastAPI",
    "sqlalchemy": "SQLAlchemy",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Azure",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "html5": "HTML",
    "html": "HTML",
    "css3": "CSS",
    "css": "CSS",
    "tailwind": "TailwindCSS",
    "tailwindcss": "TailwindCSS",
    "express": "Express.js",
    "express.js": "Express.js",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring Boot",
    "spring boot": "Spring Boot",
    "redux": "Redux",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "graphql": "GraphQL",
    "redis": "Redis",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "php": "PHP",
    "ruby": "Ruby",
    "sql": "SQL",
}

LANGUAGES_SET = {"Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "PHP", "Ruby", "SQL"}
FRAMEWORKS_SET = {"React", "Node.js", "Vue.js", "FastAPI", "Django", "Flask", "Express.js", "Spring Boot", "TailwindCSS", "Next.js"}
LIBRARIES_SET = {"SQLAlchemy", "Redux", "Pandas", "NumPy"}
DATABASES_SET = {"PostgreSQL", "MongoDB", "MySQL", "Redis", "SQLite"}
CLOUD_SET = {"AWS", "Azure", "Google Cloud"}
TOOLS_SET = {"Docker", "Kubernetes", "Git", "GitHub", "GitLab"}


def normalize_skill(skill: str) -> str:
    cleaned = skill.strip()
    key = cleaned.lower()
    return NORMALIZATION_MAP.get(key, cleaned.title() if len(cleaned) > 3 else cleaned)


class ResumeParserService:
    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider or AIProvider()

    def parse_resume_text(self, text: str) -> Dict[str, Any]:
        """Extract structured candidate profile from resume text.
        Never hallucinates unmentioned items; fields without evidence remain empty/null.
        """
        if not text or not text.strip():
            return {
                "skills": [],
                "programming_languages": [],
                "languages": [],  # backward-compatible alias
                "frameworks": [],
                "libraries": [],
                "tools": [],
                "databases": [],
                "cloud": [],
                "projects": [],
                "experience": [],
                "education": [],
                "certifications": [],
                "achievements": [],
                "years_of_experience": None,
                "inferred_role": "Software Developer",
            }

        text_lower = text.lower()
        detected_skills = set()

        for term, normalized in NORMALIZATION_MAP.items():
            pattern = r'(?<![a-zA-Z0-9_\-\.])' + re.escape(term) + r'(?![a-zA-Z0-9_\-\.])'
            if re.search(pattern, text_lower):
                detected_skills.add(normalized)

        # Categorization
        programming_languages = sorted([s for s in detected_skills if s in LANGUAGES_SET])
        frameworks = sorted([s for s in detected_skills if s in FRAMEWORKS_SET])
        libraries = sorted([s for s in detected_skills if s in LIBRARIES_SET])
        databases = sorted([s for s in detected_skills if s in DATABASES_SET])
        cloud = sorted([s for s in detected_skills if s in CLOUD_SET])
        tools = sorted([s for s in detected_skills if s in TOOLS_SET or s in CLOUD_SET])

        # All skills combined
        all_skills = sorted(list(detected_skills))

        # Infer job role
        inferred_role = "Software Developer"
        if "FastAPI" in detected_skills or "Django" in detected_skills or "Python" in detected_skills or "Node.js" in detected_skills:
            inferred_role = "Backend Developer"
        elif "React" in detected_skills or "Vue.js" in detected_skills or "Next.js" in detected_skills:
            inferred_role = "Frontend Developer"
        elif "Machine Learning" in text or "TensorFlow" in text or "PyTorch" in text:
            inferred_role = "AI/ML Engineer"

        # Extract structured projects
        projects = self._extract_projects(text, detected_skills)

        # Extract work experience
        experience = self._extract_experience(text, detected_skills)

        # Extract education
        education = self._extract_education(text)

        # Extract certifications
        certifications = self._extract_certifications(text)

        # Extract achievements
        achievements = self._extract_achievements(text)

        # Extract years of experience
        years_exp = self._extract_years_experience(text)

        # AI enhancement if configured
        if self.ai_provider.is_real_llm:
            try:
                ai_profile = self._ai_extract_profile(text)
                if ai_profile:
                    if ai_profile.get("skills"):
                        ai_skills = [normalize_skill(s) for s in ai_profile.get("skills", [])]
                        all_skills = sorted(list(set(all_skills + ai_skills)))
                    if ai_profile.get("inferred_role"):
                        inferred_role = ai_profile.get("inferred_role")
                    if ai_profile.get("projects") and isinstance(ai_profile.get("projects"), list):
                        for p in ai_profile.get("projects", []):
                            if isinstance(p, dict) and p.get("name"):
                                if not any(existing.get("name") == p.get("name") for existing in projects):
                                    projects.append(p)
            except Exception as e:
                logger.warning("AI resume parsing failed, using deterministic parser: %s", str(e))

        return {
            "skills": all_skills,
            "programming_languages": programming_languages,
            "languages": programming_languages,  # backward compatibility
            "frameworks": frameworks,
            "libraries": libraries,
            "tools": tools,
            "databases": databases,
            "cloud": cloud,
            "projects": projects,
            "experience": experience,
            "education": education,
            "certifications": certifications,
            "achievements": achievements,
            "years_of_experience": years_exp,
            "inferred_role": inferred_role,
        }

    def _extract_projects(self, text: str, detected_skills: set) -> List[Dict[str, Any]]:
        """Extract projects with name, description, and technologies explicitly mentioned."""
        projects = []
        # Pattern 1: Project/Built/Developed headers
        project_blocks = re.findall(
            r'(?:Project|Built|Developed|Created):\s*([^\n\.]+)(?:\s*[\-\–]\s*([^\n\.]+))?',
            text,
            re.IGNORECASE
        )
        for name, desc in project_blocks[:4]:
            p_name = name.strip()
            if len(p_name) >= 3:
                # Find technologies associated with this project line/desc
                combined_line = f"{p_name} {desc}".lower()
                p_techs = [s for s in detected_skills if s.lower() in combined_line]
                projects.append({
                    "name": p_name[:80],
                    "description": desc.strip()[:200] if desc else f"Project involving {', '.join(p_techs) if p_techs else p_name}",
                    "technologies": p_techs,
                })

        # Pattern 2: Dedicated Projects Section
        if not projects:
            proj_section_match = re.search(r'(?:PROJECTS|ACADEMIC PROJECTS)(.*?)(?:EXPERIENCE|EDUCATION|SKILLS|$)', text, re.DOTALL | re.IGNORECASE)
            if proj_section_match:
                lines = [l.strip() for l in proj_section_match.group(1).split("\n") if l.strip()]
                for line in lines[:3]:
                    if len(line) > 10 and not line.lower().startswith("projects"):
                        p_techs = [s for s in detected_skills if s.lower() in line.lower()]
                        projects.append({
                            "name": line[:60],
                            "description": line[:200],
                            "technologies": p_techs,
                        })

        return projects

    def _extract_experience(self, text: str, detected_skills: set) -> List[Dict[str, Any]]:
        """Extract work experience roles and companies."""
        experience = []
        role_matches = re.findall(
            r'(?:Title|Role|Position|Experience):\s*([^\n\–\-]+)(?:\s*(?:at|@|\-)\s*([^\n\.]+))?',
            text,
            re.IGNORECASE
        )
        for title, company in role_matches[:3]:
            t_clean = title.strip()
            if len(t_clean) >= 3:
                experience.append({
                    "job_title": t_clean[:60],
                    "company": company.strip()[:60] if company else None,
                    "responsibilities": [],
                    "technologies": [s for s in detected_skills if s.lower() in t_clean.lower()],
                })
        return experience

    def _extract_education(self, text: str) -> List[str]:
        """Extract degree and educational background mentions."""
        education = []
        edu_patterns = [
            r'(?:Bachelor|Master|B\.S\.|M\.S\.|B\.Tech|M\.Tech|Ph\.D|Associate)[^\n\.\,]+',
            r'(?:Computer Science|Information Technology|Software Engineering|Data Science)[^\n\.\,]*',
        ]
        for pat in edu_patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                clean_m = m.strip()
                if clean_m and clean_m not in education and len(clean_m) > 4:
                    education.append(clean_m[:80])
        return education[:3]

    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certified credentials."""
        certs = []
        cert_matches = re.findall(r'(?:Certified|Certification|Credential):\s*([^\n\.]+)', text, re.IGNORECASE)
        for c in cert_matches:
            c_clean = c.strip()
            if len(c_clean) > 3 and c_clean not in certs:
                certs.append(c_clean[:80])
        return certs[:4]

    def _extract_achievements(self, text: str) -> List[str]:
        """Extract notable honors and achievements."""
        achieve = []
        achieve_matches = re.findall(r'(?:Award|Achievement|Honor|Won|Published):\s*([^\n\.]+)', text, re.IGNORECASE)
        for a in achieve_matches:
            a_clean = a.strip()
            if len(a_clean) > 3 and a_clean not in achieve:
                achieve.append(a_clean[:100])
        return achieve[:3]

    def _extract_years_experience(self, text: str) -> Optional[int]:
        """Extract total years of experience if explicitly mentioned."""
        match = re.search(r'(\d+)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience', text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def _ai_extract_profile(self, text: str) -> Optional[Dict[str, Any]]:
        prompt = (
            f"Extract structured candidate profile from the resume text below.\n"
            f"Resume Text:\n{text[:3000]}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Extract ONLY technologies, programming languages, frameworks, libraries, tools, and projects explicitly mentioned in the text.\n"
            f"2. Do NOT hallucinate skills or technologies not present in the text.\n"
            f"3. Return JSON matching schema:\n"
            f"{{\n"
            f"  \"skills\": [\"Python\", \"FastAPI\", \"React\"],\n"
            f"  \"inferred_role\": \"Backend Developer\",\n"
            f"  \"projects\": [{{\"name\": \"Project Name\", \"description\": \"...\", \"technologies\": [\"React\"]}}],\n"
            f"  \"experience\": [{{\"job_title\": \"Software Engineer\", \"company\": \"ABC Corp\"}}]\n"
            f"}}\n"
        )

        if not self.ai_provider.is_real_llm:
            return None
        return self.ai_provider._call_llm_json(
            prompt,
            system="You extract structured data from resumes. Only report what is explicitly in the text. Return JSON only.",
            timeout=20,
        )
