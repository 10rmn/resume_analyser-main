from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re

# -------------------------
# ROLE-SKILL MAPPING
# -------------------------
ROLE_SKILL_MAP = {
    "software engineer": ["python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust", 
                          "react", "angular", "vue", "node", "nodejs", "express", "django", "flask", "spring",
                          "git", "api", "rest", "graphql", "sql", "mongodb", "postgresql", "mysql"],
    
    "frontend developer": ["javascript", "typescript", "react", "angular", "vue", "html", "css", "sass", 
                           "webpack", "babel", "redux", "nextjs", "nuxt", "tailwind", "bootstrap"],
    
    "backend developer": ["python", "java", "node", "nodejs", "go", "rust", "c#", "php", 
                          "django", "flask", "spring", "express", "fastapi", "api", "rest", "graphql",
                          "sql", "postgresql", "mysql", "mongodb", "redis", "microservices"],
    
    "full stack developer": ["javascript", "typescript", "python", "java", "react", "angular", "vue", 
                             "node", "nodejs", "django", "flask", "spring", "express", "sql", "mongodb",
                             "api", "rest", "docker", "git"],
    
    "data scientist": ["python", "r", "sql", "statistics", "machine learning", "ml", "ai", "deep learning",
                       "tensorflow", "pytorch", "keras", "pandas", "numpy", "scikit", "matplotlib", "seaborn",
                       "jupyter", "analysis", "modeling", "algorithms"],
    
    "machine learning engineer": ["python", "tensorflow", "pytorch", "keras", "scikit", "ml", "ai", 
                                  "deep learning", "nlp", "computer vision", "models", "algorithms",
                                  "pandas", "numpy", "cloud", "aws", "gcp", "azure"],
    
    "data engineer": ["python", "java", "scala", "sql", "spark", "hadoop", "kafka", "airflow", 
                      "etl", "data pipeline", "big data", "aws", "gcp", "azure", "snowflake", 
                      "redshift", "databricks"],
    
    "devops engineer": ["docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "jenkins", "gitlab",
                        "terraform", "ansible", "linux", "bash", "python", "monitoring", "prometheus",
                        "grafana", "deployment", "automation"],
    
    "cloud engineer": ["aws", "gcp", "azure", "cloud", "docker", "kubernetes", "terraform", "serverless",
                       "lambda", "s3", "ec2", "networking", "security", "devops"],
    
    "mobile developer": ["ios", "android", "swift", "kotlin", "java", "react native", "flutter", "dart",
                         "mobile", "app", "xcode", "android studio"],
    
    "qa engineer": ["testing", "automation", "selenium", "pytest", "junit", "test", "qa", "quality",
                    "cypress", "jenkins", "ci/cd", "bug", "debug"],
}

# -------------------------
# CATEGORY KEYWORD GROUPS
# -------------------------
CRITICAL = {
    "python", "java", "javascript", "typescript", "c++", "sql", "nosql",
    "data", "machine", "learning", "ml", "ai", "statistics",
    "nlp", "deep", "cloud", "models", "algorithms", "database",
    "api", "rest", "microservices", "kubernetes", "docker",
    "react", "angular", "vue", "node", "django", "flask",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit"
}

GOOD = {
    "aws", "gcp", "azure", "devops", "ci", "cd",
    "pipelines", "deployment", "spark", "analysis",
    "insights", "agile", "scrum", "git", "github",
    "monitoring", "testing", "automation", "security",
    "optimization", "scalability", "architecture"
}

OPTIONAL = {
    "team", "culture", "join", "environment", "best", 
    "community", "develop", "collaborate", "communication",
    "leadership", "problem", "solving"
}

# -------------------------
# ROLE DETECTION
# -------------------------
def detect_roles_from_skills(text: str):
    """Detect which job roles a person is qualified for based on their skills"""
    text_lower = text.lower()
    role_matches = {}
    
    for role, skills in ROLE_SKILL_MAP.items():
        match_count = sum(1 for skill in skills if skill in text_lower)
        if match_count > 0:
            role_matches[role] = match_count
    
    # Sort by match count
    sorted_roles = sorted(role_matches.items(), key=lambda x: x[1], reverse=True)
    return [role for role, count in sorted_roles if count >= 2]  # At least 2 matching skills


def enhance_text_with_roles(text: str, detected_roles: list):
    """Add detected roles to text for better matching"""
    role_text = " ".join(detected_roles)
    return f"{text} {role_text}"


# -------------------------
# SMART CODE DETECTOR
# -------------------------
def looks_like_code(text: str) -> bool:
    """Avoid false positives. Only detect code if 3 or more signatures are present."""
    patterns = [
        r"\bdef\s+\w+\(",
        r"\bclass\s+\w+:",
        r"\bimport\s+\w+",
        r"\bfrom\s+\w+\s+import",
        r"\breturn\b",
        r"\bprint\s*\(",
        r"\bfor\s+\w+\s+in\b",
        r"\bwhile\s+\w+",
        r"\btry:\b",
        r"\bexcept\b"
    ]

    count = 0
    for p in patterns:
        if re.search(p, text, re.MULTILINE):
            count += 1

    return count >= 3



# -------------------------
# MAIN MATCH FUNCTION
# -------------------------
def match_resume_to_jd(resume_text: str, jd_text: str):

    # Invalid JD (pasted Python code)
    if looks_like_code(jd_text):
        return 0.0, {
            "critical": ["❌ Invalid JD. You pasted code instead of a job description."],
            "good": [],
            "optional": []
        }

    # Detect roles from resume skills
    detected_roles = detect_roles_from_skills(resume_text)
    print(f"Detected roles from resume: {detected_roles}")
    
    # Enhance resume text with detected roles for better matching
    enhanced_resume = enhance_text_with_roles(resume_text, detected_roles)

    # Clean and normalize text
    resume_clean = enhanced_resume.lower()
    jd_clean = jd_text.lower()

    # Vectorizer
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000, min_df=1)
    
    try:
        tfidf = vectorizer.fit_transform([resume_clean, jd_clean])
    except Exception as e:
        print(f"TF-IDF error: {e}")
        return 0.0, {"critical": [], "good": [], "optional": []}

    a = tfidf[0].toarray()[0]
    b = tfidf[1].toarray()[0]

    # Score (cosine similarity)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        score = 0.0
    else:
        score = np.dot(a, b) / (norm_a * norm_b)

    # Clamp score between 0 and 1
    score = max(0.0, min(score, 1.0))

    # Analyze keywords - find what's missing and what's matched
    feature_names = vectorizer.get_feature_names_out()
    
    # Get top keywords from JD
    jd_indices = b.argsort()[::-1]
    missing_keywords = []
    matched_keywords = []
    
    for idx in jd_indices:
        if b[idx] > 0.01:  # Only consider significant terms
            word = feature_names[idx]
            if len(word) > 2:
                # Check if word exists in resume
                if a[idx] < 0.01:
                    missing_keywords.append(word)
                elif a[idx] > 0.01:
                    matched_keywords.append(word)
        if len(missing_keywords) >= 50 and len(matched_keywords) >= 50:
            break

    # Categorize missing keywords
    missing_categorized = {
        "critical": [w for w in missing_keywords if w in CRITICAL][:10],
        "good": [w for w in missing_keywords if w in GOOD][:10],
        "optional": [
            w for w in missing_keywords
            if w not in CRITICAL and w not in GOOD
        ][:30],
    }
    
    # Categorize matched keywords
    matched_categorized = {
        "critical": [w for w in matched_keywords if w in CRITICAL][:15],
        "good": [w for w in matched_keywords if w in GOOD][:15],
        "optional": [
            w for w in matched_keywords
            if w not in CRITICAL and w not in GOOD
        ][:20],
    }

    # If no missing keywords, show what you have instead
    result = {
        "missing": missing_categorized,
        "matched": matched_categorized,
        "detected_roles": detected_roles
    }

    print(f"Match score: {score}")
    print(f"Missing keywords: {missing_categorized}")
    print(f"Matched keywords: {matched_categorized}")

    return score, result
