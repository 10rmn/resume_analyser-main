import os
from typing import List
import google.generativeai as genai

API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)

def rewrite_bullets_with_llm(text: str, max_alternatives: int = 2) -> List[str]:
    """
    Rewrites resume bullets using Gemini 1.5 Flash.
    """

    prompt = f"""
Rewrite this resume bullet point into {max_alternatives} improved versions.
Rules:
- 1 line only
- Start with strong action verbs
- Professional & concise
- No "I", "my", "we", etc.
- ATS-friendly
- Do NOT create fake numbers

Bullet:
{text}
"""

    if not API_KEY:
        return [f"Improved: {text}", f"Enhanced: {text}"][:max_alternatives]

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        lines = [
            l.strip("-• ") 
            for l in response.text.split("\n") 
            if l.strip()
        ]
        return lines[:max_alternatives]

    except Exception:
        return [text]
