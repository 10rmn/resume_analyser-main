import io
import pdfplumber
from docx import Document

def extract_text_from_file(uploaded):
    name = uploaded.name.lower()
    data = uploaded.read()

    if name.endswith(".pdf"):
        text_parts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)

    elif name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        return "\n".join([p.text for p in doc.paragraphs])

    return data.decode("utf-8", errors="ignore")
