"""A compact skills taxonomy with aliases, and a matcher that finds them in text."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, List, Set

# canonical name -> (category, [aliases])
SKILLS: Dict[str, tuple[str, list[str]]] = {
    # Languages
    "Python": ("Languages", ["python", "python3"]),
    "Java": ("Languages", ["java"]),
    "JavaScript": ("Languages", ["javascript", "js", "es6"]),
    "TypeScript": ("Languages", ["typescript", "ts"]),
    "C++": ("Languages", ["c++", "cpp"]),
    "C": ("Languages", ["c programming", "ansi c"]),
    "Go": ("Languages", ["golang"]),
    "Kotlin": ("Languages", ["kotlin"]),
    "SQL": ("Languages", ["sql", "t-sql", "pl/sql"]),
    "R": ("Languages", ["r programming", "rstudio"]),
    "HTML": ("Languages", ["html", "html5"]),
    "CSS": ("Languages", ["css", "css3", "scss", "sass"]),
    "Bash": ("Languages", ["bash", "shell scripting"]),
    # Web
    "React": ("Web", ["react", "react.js", "reactjs"]),
    "Next.js": ("Web", ["next.js", "nextjs"]),
    "Angular": ("Web", ["angular"]),
    "Vue": ("Web", ["vue", "vue.js", "vuejs"]),
    "Node.js": ("Web", ["node.js", "nodejs", "node"]),
    "Express": ("Web", ["express", "express.js", "expressjs"]),
    "Django": ("Web", ["django"]),
    "Flask": ("Web", ["flask"]),
    "FastAPI": ("Web", ["fastapi"]),
    "Spring Boot": ("Web", ["spring boot", "springboot", "spring"]),
    "REST APIs": ("Web", ["rest", "rest api", "rest apis", "restful"]),
    "GraphQL": ("Web", ["graphql"]),
    "Tailwind CSS": ("Web", ["tailwind", "tailwindcss"]),
    "Redux": ("Web", ["redux"]),
    # Data & ML
    "Machine Learning": ("Data & AI", ["machine learning", "ml"]),
    "Deep Learning": ("Data & AI", ["deep learning", "neural networks"]),
    "NLP": ("Data & AI", ["nlp", "natural language processing"]),
    "Computer Vision": ("Data & AI", ["computer vision", "opencv"]),
    "Generative AI": ("Data & AI", ["generative ai", "genai", "gen ai"]),
    "LLMs": ("Data & AI", ["llm", "llms", "large language models"]),
    "RAG": ("Data & AI", ["rag", "retrieval augmented generation", "retrieval-augmented generation"]),
    "LangChain": ("Data & AI", ["langchain"]),
    "Prompt Engineering": ("Data & AI", ["prompt engineering"]),
    "TensorFlow": ("Data & AI", ["tensorflow", "keras"]),
    "PyTorch": ("Data & AI", ["pytorch", "torch"]),
    "scikit-learn": ("Data & AI", ["scikit-learn", "sklearn", "scikit learn"]),
    "Pandas": ("Data & AI", ["pandas"]),
    "NumPy": ("Data & AI", ["numpy"]),
    "XGBoost": ("Data & AI", ["xgboost", "lightgbm", "gradient boosting"]),
    "Statistics": ("Data & AI", ["statistics", "statistical analysis", "hypothesis testing", "a/b testing"]),
    "Data Analysis": ("Data & AI", ["data analysis", "data analytics", "exploratory data analysis", "eda"]),
    "Data Visualization": ("Data & AI", ["data visualization", "matplotlib", "seaborn", "plotly"]),
    "Power BI": ("Data & AI", ["power bi", "powerbi"]),
    "Tableau": ("Data & AI", ["tableau"]),
    "Excel": ("Data & AI", ["excel", "ms excel", "advanced excel"]),
    "Spark": ("Data & AI", ["spark", "pyspark", "apache spark"]),
    "Streamlit": ("Data & AI", ["streamlit"]),
    # Databases
    "MongoDB": ("Databases", ["mongodb", "mongo", "mongoose"]),
    "PostgreSQL": ("Databases", ["postgresql", "postgres"]),
    "MySQL": ("Databases", ["mysql"]),
    "Redis": ("Databases", ["redis"]),
    "Firebase": ("Databases", ["firebase", "firestore"]),
    "Vector Databases": ("Databases", ["vector database", "faiss", "pinecone", "chromadb", "chroma"]),
    # Cloud & DevOps
    "AWS": ("Cloud & DevOps", ["aws", "amazon web services", "ec2", "s3", "lambda"]),
    "Azure": ("Cloud & DevOps", ["azure"]),
    "GCP": ("Cloud & DevOps", ["gcp", "google cloud"]),
    "Docker": ("Cloud & DevOps", ["docker", "containerization"]),
    "Kubernetes": ("Cloud & DevOps", ["kubernetes", "k8s"]),
    "CI/CD": ("Cloud & DevOps", ["ci/cd", "github actions", "jenkins", "continuous integration"]),
    "Linux": ("Cloud & DevOps", ["linux", "unix"]),
    "Git": ("Cloud & DevOps", ["git", "github", "gitlab", "version control"]),
    "MLOps": ("Cloud & DevOps", ["mlops", "mlflow", "model deployment"]),
    # Practices & soft skills
    "Data Structures & Algorithms": ("Fundamentals", ["data structures", "algorithms", "dsa"]),
    "OOP": ("Fundamentals", ["oop", "object oriented", "object-oriented"]),
    "System Design": ("Fundamentals", ["system design"]),
    "Unit Testing": ("Fundamentals", ["unit testing", "pytest", "jest", "testing", "tdd"]),
    "Agile": ("Fundamentals", ["agile", "scrum"]),
    "JWT Authentication": ("Fundamentals", ["jwt", "authentication", "oauth"]),
    "Communication": ("Soft Skills", ["communication", "presentation skills"]),
    "Teamwork": ("Soft Skills", ["teamwork", "collaboration", "team player", "cross-functional"]),
    "Problem Solving": ("Soft Skills", ["problem solving", "problem-solving", "analytical skills"]),
    "Leadership": ("Soft Skills", ["leadership", "mentoring", "led a team"]),
}

# Ambiguous short aliases that need surrounding context to count
_CONTEXT_REQUIRED = {"node", "spring", "ts", "js", "ml", "rest", "testing", "go", "c", "r", "eda", "chroma", "s3", "lambda"}


@lru_cache(maxsize=None)
def _pattern(alias: str) -> re.Pattern:
    # Word-boundary match that also works for tokens like c++, node.js, ci/cd
    return re.compile(r"(?<![\w+#.])" + re.escape(alias) + r"(?![\w+#])", re.IGNORECASE)


def _ambiguous_hit(alias: str, text: str) -> bool:
    """Short words like 'rest' or 'node' only count as skills when written as an acronym
    (REST, ML) or inside a list (', Node,' / 'Skills: Node')."""
    if re.search(rf"(?<![\w.]){re.escape(alias.upper())}(?!\w)", text):
        return True
    in_list = rf"(?:^|[,/|;:(•]\s*){re.escape(alias)}(?=\s*(?:[,/|;)]|$))"
    return re.search(in_list, text, re.IGNORECASE | re.MULTILINE) is not None


def extract_skills(text: str) -> Set[str]:
    """Return canonical skill names found in the text."""
    found: Set[str] = set()
    lowered = text.lower()
    for canonical, (_, aliases) in SKILLS.items():
        for alias in aliases:
            if alias in _CONTEXT_REQUIRED:
                if alias in {"go", "c", "r"}:
                    continue  # too ambiguous as bare words; rely on longer aliases
                if _ambiguous_hit(alias, text):
                    found.add(canonical)
                    break
                continue
            if alias in lowered and _pattern(alias).search(text):
                found.add(canonical)
                break
    return found


def category_of(skill: str) -> str:
    return SKILLS.get(skill, ("Other", []))[0]


def group_by_category(skills: Set[str] | List[str]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for s in sorted(skills, key=str.lower):
        groups.setdefault(category_of(s), []).append(s)
    return groups
