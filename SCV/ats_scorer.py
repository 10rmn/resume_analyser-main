import re
import os
from typing import Dict, List, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)


def calculate_ats_score(resume_text: str, parsed_data: dict) -> Dict:
    """
    Calculate ATS compliance score using rule-based + LLM approach.
    Returns a dict with overall score, breakdown, and recommendations.
    """
    
    # Rule-based scoring (0-70 points)
    rule_score, rule_breakdown = calculate_rule_based_score(resume_text, parsed_data)
    
    # LLM-based scoring (0-30 points)
    llm_score, llm_feedback = calculate_llm_score(resume_text)
    
    # Combined score
    total_score = rule_score + llm_score
    
    return {
        "total_score": round(total_score, 1),
        "rule_based_score": round(rule_score, 1),
        "llm_score": round(llm_score, 1),
        "rule_breakdown": rule_breakdown,
        "llm_feedback": llm_feedback,
        "grade": get_grade(total_score)
    }


def calculate_rule_based_score(resume_text: str, parsed_data: dict) -> Tuple[float, Dict]:
    """
    Rule-based ATS compliance checks (max 70 points).
    """
    score = 0
    breakdown = {}
    
    # 1. Contact Information (10 points)
    contact_score = 0
    contact = parsed_data.get("contact", {})
    if contact.get("emails"):
        contact_score += 5
    if contact.get("phones"):
        contact_score += 3
    if contact.get("links"):
        contact_score += 2
    score += contact_score
    breakdown["contact_info"] = {"score": contact_score, "max": 10}
    
    # 2. Standard Section Headings (15 points)
    section_score = 0
    standard_sections = ["experience", "education", "skills", "summary", "projects"]
    sections = parsed_data.get("sections", {})
    found_sections = sum(1 for s in standard_sections if s in sections)
    section_score = (found_sections / len(standard_sections)) * 15
    score += section_score
    breakdown["standard_sections"] = {"score": round(section_score, 1), "max": 15}
    
    # 3. Skills Detection (15 points)
    skills = parsed_data.get("extracted_skills", [])
    skill_count = len(skills)
    if skill_count >= 10:
        skills_score = 15
    elif skill_count >= 5:
        skills_score = 10
    elif skill_count >= 3:
        skills_score = 5
    else:
        skills_score = 0
    score += skills_score
    breakdown["skills_detection"] = {"score": skills_score, "max": 15, "count": skill_count}
    
    # 4. Resume Length (10 points)
    word_count = len(resume_text.split())
    if 400 <= word_count <= 800:
        length_score = 10
    elif 300 <= word_count <= 1000:
        length_score = 7
    else:
        length_score = 3
    score += length_score
    breakdown["resume_length"] = {"score": length_score, "max": 10, "word_count": word_count}
    
    # 5. Bullet Points (10 points)
    bullet_patterns = r'[•\-\*●○▪]'
    bullet_count = len(re.findall(bullet_patterns, resume_text))
    if bullet_count >= 10:
        bullet_score = 10
    elif bullet_count >= 5:
        bullet_score = 7
    elif bullet_count >= 3:
        bullet_score = 4
    else:
        bullet_score = 0
    score += bullet_score
    breakdown["bullet_points"] = {"score": bullet_score, "max": 10, "count": bullet_count}
    
    # 6. Action Verbs (10 points)
    action_verbs = [
        "developed", "built", "designed", "achieved", "created", "led", "managed",
        "optimized", "implemented", "analyzed", "engineered", "enhanced", "improved",
        "coordinated", "executed", "deployed", "established", "delivered"
    ]
    text_lower = resume_text.lower()
    verb_count = sum(1 for verb in action_verbs if verb in text_lower)
    if verb_count >= 8:
        verb_score = 10
    elif verb_count >= 5:
        verb_score = 7
    elif verb_count >= 3:
        verb_score = 4
    else:
        verb_score = 0
    score += verb_score
    breakdown["action_verbs"] = {"score": verb_score, "max": 10, "count": verb_count}
    
    return score, breakdown


def calculate_llm_score(resume_text: str) -> Tuple[float, str]:
    """
    LLM-based ATS compliance evaluation (max 30 points).
    Uses Gemini to assess content quality, keyword optimization, and ATS-friendliness.
    """
    
    if not API_KEY:
        return 20.0, "LLM evaluation unavailable (no API key)"
    
    prompt = f"""
You are an expert ATS (Applicant Tracking System) and recruitment specialist evaluating a resume.

Analyze this resume critically and provide honest, specific feedback on what's MISSING or WEAK:

Resume:
{resume_text[:3000]}

Provide a detailed evaluation in this EXACT format:

SCORE: [number from 0-30]

FEEDBACK:
**What's Missing:**
- [List 2-3 specific things that are missing or inadequate]

**What Needs Improvement:**
- [List 2-3 specific weaknesses or areas that need work]

**What to Add:**
- [List 2-3 concrete suggestions for content to add]

Be specific, critical, and actionable. Focus on:
- Missing quantifiable metrics and achievements
- Weak or generic language
- Missing technical skills or certifications
- Lack of keywords for ATS optimization
- Poor structure or formatting issues
- Missing sections (summary, projects, etc.)
"""
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        result = response.text
        
        # Parse score
        score_match = re.search(r'SCORE:\s*(\d+(?:\.\d+)?)', result)
        score = float(score_match.group(1)) if score_match else 20.0
        score = min(30, max(0, score))  # Clamp between 0-30
        
        # Parse feedback - get everything after FEEDBACK:
        feedback_match = re.search(r'FEEDBACK:\s*(.+)', result, re.DOTALL)
        if feedback_match:
            feedback = feedback_match.group(1).strip()
            # Clean up the feedback
            feedback = feedback.replace('**', '').strip()
        else:
            feedback = "Unable to generate detailed feedback. Please review your resume structure and content."
        
        return score, feedback
        
    except Exception as e:
        print(f"LLM scoring error: {e}")
        return 15.0, f"Error generating feedback: {str(e)}. Please ensure your resume has clear sections, quantifiable achievements, and relevant keywords."


def get_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A+ (Excellent)"
    elif score >= 80:
        return "A (Very Good)"
    elif score >= 70:
        return "B (Good)"
    elif score >= 60:
        return "C (Fair)"
    elif score >= 50:
        return "D (Poor)"
    else:
        return "F (Needs Improvement)"
