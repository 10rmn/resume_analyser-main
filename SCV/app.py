import os
import json
import streamlit as st

from utils.extract import extract_text_from_file
from utils.nlp_utils_simple import clean_text, extract_skills_and_keywords
from utils.parse_resume import parse_resume_text
from matcher import match_resume_to_jd
from llm_wrapper import rewrite_bullets_with_llm


# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="SmartCV (Gemini)", layout="wide")
st.title("SmartCV — Gemini AI Powered Resume Optimization")


# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("Upload Resume")
    resume_file = st.file_uploader("Upload Resume (PDF / DOCX)", type=["pdf", "docx"])

    st.header("Job Description")
    jd_text = st.text_area("Paste Job Description (optional)", height=200)

    st.header("AI Rewrite Options")
    rewrite = st.checkbox("Rewrite Resume Bullets Using Gemini", value=True)
    max_suggestions = st.slider("Rewrite Versions per Bullet", 1, 5, 2)
    debug_print = st.checkbox("Print parsed JSON to console", value=False)


# ---------------- STOP IF NO FILE ----------------
if not resume_file:
    st.info("Upload your resume to proceed.")
    st.stop()


# ---------------- EXTRACT & PARSE TEXT ----------------
raw_text = extract_text_from_file(resume_file)
if not raw_text or not str(raw_text).strip():
    st.error("Error extracting text. Try another file.")
    st.stop()

# Parse into structured form (blocks, lines, header/contact, sections)
parsed = parse_resume_text(raw_text)
# Use the parsed flat lines as the cleaned representation for downstream steps
cleaned = "\n".join(parsed.get("lines", []))

# Show parsed header info
st.subheader("Candidate")
st.write(parsed.get("name") or "Unknown")
st.write(parsed.get("contact") or {})

# Debug: optionally print parsed JSON to the server console
if 'debug_print' in locals() and debug_print:
    try:
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception:
        print(parsed)


# ---------------- SKILLS SECTION ----------------
st.subheader("Extracted Skills")
skills, keywords = extract_skills_and_keywords(cleaned)
st.write(", ".join(skills) if skills else "No skills detected.")


# ---------------- KEYWORDS SECTION ----------------
st.subheader("Top Keywords")
st.write(", ".join(keywords[:30]))


# ---------------- JD MATCH SECTION ----------------
# JD Match Display
if jd_text.strip():
    score, missing = match_resume_to_jd(cleaned, jd_text)

    st.subheader("JD Match Score")
    st.metric("Match %", f"{score * 100:.1f}%")

    st.subheader("Missing Keywords Breakdown")
    
    st.write("🔴 **Critical:**", ", ".join(missing["critical"]) or "None")
    st.write("🟡 **Good-to-Have:**", ", ".join(missing["good"]) or "None")
    st.write("⚪ **Optional:**", ", ".join(missing["optional"]) or "None")


# ---------------- SMART BULLET DETECTOR ----------------
def is_resume_bullet(line: str):
    # All possible resume bullet characters
    bullet_symbols = ("•", "-", "*", "·", "●", "○", "▪", "►", "‣", "▸", "▹", "‣", "–", "—", "⦿", "◆", "■", "●", "•", "")

    verbs = [
        "developed", "built", "designed", "achieved", "created",
        "led", "optimized", "implemented", "managed", "analyzed",
        "engineered", "enhanced", "constructed", "executed",
        "deployed", "built", "improved", "coordinated"
    ]

    l = line.strip().lower()

    return (
        l.startswith(bullet_symbols) or
        any(l.startswith(v) for v in verbs)
    )



# ---------------- REWRITE SECTION ----------------
if rewrite:
    st.subheader("Gemini AI Rewrite Suggestions")

    # Filter only REAL resume bullets
    lines = [
        l.strip()
        for l in cleaned.split("\n")
        if len(l.strip()) > 20 and is_resume_bullet(l.strip())
    ][:30]

    if not lines:
        st.warning("No valid resume bullet points detected for rewriting.")
    else:
        suggestions = {}
        progress = st.progress(0)

        for i, line in enumerate(lines[:10]):
            new_versions = rewrite_bullets_with_llm(line, max_suggestions)
            suggestions[line] = new_versions
            progress.progress((i + 1) / len(lines[:10]))

        progress.empty()

        # Display rewritten bullets
        for orig, alts in suggestions.items():
            st.markdown("### Original")
            st.write(orig)

            st.markdown("### Gemini Rewrites")
            for a in alts:
                st.write(f"- {a}")

            st.write("---")


st.success("Resume optimization complete!")
