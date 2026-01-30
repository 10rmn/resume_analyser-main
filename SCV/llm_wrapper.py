import os
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)


def rewrite_bullets_with_llm(text: str, max_alternatives: int = 2) -> List[str]:
    """
    Strong ATS-friendly rewrite generator (Gemini 1.5 Flash).
    Ensures actual rewritten bullets instead of garbage outputs.
    """

    prompt = f"""
You are a professional ATS Resume Optimizer LLM.

Rewrite the following resume bullet point into EXACTLY {max_alternatives} improved versions.

RULES:
- Each version MUST be different from the original.
- MUST start with a strong action verb.
- MUST be ONE line only.
- Professional, concise, ATS-friendly.
- DO NOT add fake metrics or achievements.
- DO NOT return phrases like “Enhanced version of…” or “Optimized wording…”.
- MUST rewrite the bullet into real resume language.

Original Bullet:
{text}

Return ONLY the rewritten bullet points, one per line.
"""

    # Fallback if no API key
    if not API_KEY:
        return [
            f"Improved: Enhanced {text[:50]}...",
            f"Alternative: Refined {text[:50]}..."
        ][:max_alternatives]

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        rewritten = []
        for line in response.text.split("\n"):
            cleaned = line.strip("•- ").strip()

            # ignore garbage
            if not cleaned:
                continue
            if cleaned.lower() == text.lower():
                continue

            # remove LLM bad outputs
            banned = ["enhanced version", "optimized wording", "improved version"]
            if any(b in cleaned.lower() for b in banned):
                continue

            if len(cleaned.split()) < 4:
                continue

            rewritten.append(cleaned)

        return rewritten[:max_alternatives]

    except Exception:
        return [f"Improved: {text}"]
