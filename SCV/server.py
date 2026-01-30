from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json

from utils.extract import extract_text_from_file
from utils.parse_resume import parse_resume_text
from utils.nlp_utils_simple import extract_skills_and_keywords
from matcher import match_resume_to_jd
from ats_scorer import calculate_ats_score

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _UploadedFileLike:
    """Adapter to mimic Streamlit's UploadedFile interface."""
    def __init__(self, filename: str, data: bytes):
        self.name = filename
        self._data = data

    def read(self):
        return self._data


@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a resume file."""
    data = await file.read()
    uploaded = _UploadedFileLike(file.filename, data)

    try:
        raw_text = extract_text_from_file(uploaded)
    except Exception as e:
        return {"error": f"failed to extract text: {e}"}

    parsed = parse_resume_text(raw_text)
    
    # Store raw text for JD matching
    parsed["raw_text"] = raw_text
    
    # Extract skills using the NLP utils
    cleaned_text = "\n".join(parsed.get("lines", []))
    try:
        skills, keywords = extract_skills_and_keywords(cleaned_text)
        parsed["extracted_skills"] = skills
        parsed["extracted_keywords"] = keywords[:30]
    except Exception as e:
        parsed["extracted_skills"] = []
        parsed["extracted_keywords"] = []
        print(f"Error extracting skills: {e}")

    # Calculate ATS Score
    try:
        ats_result = calculate_ats_score(raw_text, parsed)
        parsed["ats_score"] = ats_result
    except Exception as e:
        parsed["ats_score"] = {
            "total_score": 0,
            "error": str(e)
        }
        print(f"Error calculating ATS score: {e}")

    # Print to console for debugging
    try:
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception:
        print(parsed)

    return parsed


@app.post("/match")
async def match_jd(data: dict):
    """Match resume against job description."""
    try:
        resume_text = data.get("resume_text", "")
        jd_text = data.get("jd_text", "")
        
        print(f"Resume text length: {len(resume_text)}")
        print(f"JD text length: {len(jd_text)}")
        print(f"Resume text preview: {resume_text[:200]}")
        print(f"JD text preview: {jd_text[:200]}")
        
        if not resume_text or not jd_text:
            return {"error": "Both resume_text and jd_text are required"}
        
        if len(resume_text) < 50:
            return {"error": "Resume text is too short. Please upload a valid resume."}
        
        score, missing = match_resume_to_jd(resume_text, jd_text)
        return {
            "score": float(score),
            "missing_keywords": missing
        }
    except Exception as e:
        print(f"Match error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
