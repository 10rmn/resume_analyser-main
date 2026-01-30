import re
import nltk
from collections import Counter
from difflib import get_close_matches

# Extended skill list
COMMON_SKILLS = {
    "python","java","c","c++","javascript","sql","mysql","postgresql",
    "react","node","aws","docker","git","nlp","machine learning",
    "deep learning","pandas","numpy","sklearn","opencv","flask","django",
    "hadoop","spark","gcp","pytorch","tensorflow","data analysis",
    "data science","cloud"
}

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def extract_skills_and_keywords(text: str):
    words = nltk.word_tokenize(text.lower())

    detected_skills = set()
    for skill in COMMON_SKILLS:
        if get_close_matches(skill, words, cutoff=0.8):
            detected_skills.add(skill)

    nouns = [w for w in words if len(w) > 3 and w.isalpha()]
    freq = Counter(nouns)
    keywords = [w for w, _ in freq.most_common(40)]

    return sorted(detected_skills), keywords
