import re
import nltk
from collections import Counter
import spacy

try:
    nltk.data.find("tokenizers/punkt")
except:
    nltk.download("punkt")

nlp = spacy.load("en_core_web_sm")

COMMON_SKILLS = {
    "python","java","c","c++","javascript","react","node",
    "sql","mysql","postgresql","aws","docker","git",
    "nlp","machine learning","deep learning","pandas",
    "numpy","sklearn","opencv","flask","django"
}

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def extract_skills_and_keywords(text: str):
    doc = nlp(text.lower())
    tokens = [t.lemma_ for t in doc if t.is_alpha]

    skills = sorted({s for s in COMMON_SKILLS if s in text.lower()})

    nouns = [t.lemma_ for t in doc if t.pos_ in ("NOUN", "PROPN")]
    freq = Counter(nouns)
    keywords = [w for w, _ in freq.most_common(40)]

    return skills, keywords
