"""Resume parsing helpers.

Provides functions to convert raw resume text into a structured JSON-like dict.

Features:
- Merge hyphenated words broken across lines ("optimi-\nzation" -> "optimization").
- Remove repeated headers/footers that appear across pages.
- Preprocess into blocks (paragraph groups) and per-line lists.
- Extract header info (name, emails, phones, links) from the first ~15 lines.
- Segment the resume into common sections using fuzzy matching of section headers.

This module is intentionally dependency-light (stdlib only) so it can be used
inside the Streamlit app without extra installs.
"""
from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional


SECTION_PATTERNS = {
    "experience": ["experience", "work experience", "professional experience", "employment history"],
    "education": ["education", "academic details", "academic background"],
    "projects": ["projects", "academic projects", "personal projects"],
    "skills": ["skills", "technical skills", "skills & tools", "technologies"],
    "certifications": ["certifications", "certificates"],
    "awards": ["awards", "achievements", "honors"],
    "summary": ["summary", "profile", "about me"],
}


def _merge_hyphenated_words(text: str) -> str:
    """Join words split across lines with hyphenation.

    E.g. "optimi-\nzation" -> "optimization".
    """
    # handle word-
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
    return text


def _normalize_newlines(text: str) -> str:
    text = text.replace("\r", "\n")
    # collapse many blank lines to a double-newline marker (block separator)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def preprocess_text_into_blocks(raw_text: str) -> Tuple[List[List[str]], List[str]]:
    """Return a list of blocks (each block is a list of stripped lines) and flat lines list.

    Behavior:
    - Merge hyphenated words.
    - Normalize newlines and treat two consecutive newlines as block separators.
    - Within each block, split into lines and strip whitespace.
    - Remove empty lines within blocks.
    """
    t = _merge_hyphenated_words(raw_text)
    t = _normalize_newlines(t)

    blocks_raw = [b for b in t.split("\n\n") if b.strip()]
    blocks: List[List[str]] = []
    for b in blocks_raw:
        lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
        if lines:
            blocks.append(lines)

    # flat lines (no empty lines) preserving original capitalization
    flat_lines: List[str] = [ln for block in blocks for ln in block]
    return blocks, flat_lines


def _likely_name(line: str) -> bool:
    """Heuristic to detect a name line: 1-4 words, mostly alphabetic, Title Case-ish.
    Excludes lines containing words like 'resume' or 'cv'.
    """
    if not line or len(line.split()) > 4:
        return False
    low = line.lower()
    if any(x in low for x in ("resume", "cv", "curriculum", "address", "phone", "email")):
        return False
    words = line.split()
    alpha_words = sum(1 for w in words if re.match(r"^[A-Za-z'-]+$", w))
    if alpha_words < max(1, len(words) // 2):
        return False
    # Title case or all-caps are common for names
    title_like = sum(1 for w in words if w[0].isupper())
    return title_like >= 1


def extract_header_info(lines: List[str], scan_lines: int = 15) -> Tuple[Optional[str], Dict[str, List[str]], List[str]]:
    """Extract candidate name and contact info from the first N lines.

    Returns (name_or_none, contact_dict, remaining_lines)
    contact_dict contains keys: emails, phones, links
    The returned remaining_lines will have header lines removed so downstream
    segmentation operates on the body.
    """
    header_block = lines[:scan_lines]

    emails: List[str] = []
    phones: List[str] = []
    links: List[str] = []

    email_re = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
    phone_re = re.compile(r"(\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}")
    url_re = re.compile(r"https?://[\w\.-/]+|www\.[\w\.-/]+|linkedin\.com/[^\s,]+|github\.com/[^\s,]+", re.I)

    name_candidate: Optional[str] = None
    name_index: Optional[int] = None

    for i, ln in enumerate(header_block):
        # emails
        for m in email_re.findall(ln):
            if m not in emails:
                emails.append(m)

        # phones
        for m in phone_re.findall(ln):
            # phone_re uses groups; join
            if isinstance(m, tuple):
                candidate = "".join(m)
            else:
                candidate = m
            candidate = candidate.strip()
            if candidate and candidate not in phones and len(re.sub(r"\D", "", candidate)) >= 7:
                phones.append(candidate)

        # links
        for m in url_re.findall(ln):
            if m not in links:
                links.append(m)

        # name heuristic (prefer earlier lines)
        if name_candidate is None and _likely_name(ln):
            name_candidate = ln.strip()
            name_index = i

    # Build contact dict
    contact = {"emails": emails, "phones": phones, "links": links}

    # Strip out header lines: anything up to name_index (inclusive) and lines that contained email/phone/link
    header_lines_set = set()
    if name_index is not None:
        for j in range(0, name_index + 1):
            header_lines_set.add(header_block[j])

    # also add lines that had contact info
    for ln in header_block:
        if email_re.search(ln) or phone_re.search(ln) or url_re.search(ln):
            header_lines_set.add(ln)

    remaining = [ln for ln in lines if ln not in header_lines_set]

    return name_candidate, contact, remaining


def _normalize_for_matching(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_section_header(line: str) -> Optional[str]:
    """Return the matched section name if the line looks like a section header."""
    ln = _normalize_for_matching(line)
    # exact contains check first
    for sect, patterns in SECTION_PATTERNS.items():
        for p in patterns:
            if p in ln:
                return sect

    # fuzzy match: compare tokenized small line to patterns
    # consider short lines (<=6 words) or all-caps
    words = ln.split()
    if len(words) > 8:
        return None

    for sect, patterns in SECTION_PATTERNS.items():
        for p in patterns:
            score = SequenceMatcher(None, ln, p).ratio()
            if score > 0.78:
                return sect

    # also accept lines that are short and appear to be header-like (all caps and short)
    if line.strip() == line.strip().upper() and 1 <= len(line.split()) <= 6:
        # try to map to best matching section
        best: Tuple[Optional[str], float] = (None, 0.0)
        for sect, patterns in SECTION_PATTERNS.items():
            for p in patterns:
                score = SequenceMatcher(None, ln, p).ratio()
                if score > best[1]:
                    best = (sect, score)
        if best[0] and best[1] > 0.5:
            return best[0]

    return None


# ---------------------------
# Section parsing functions
# ---------------------------


DATE_RE = re.compile(r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{4}|\b\d{4}\b)\s*[-–—to]{1,3}\s*(?:Present|Now|Present\.|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+\d{4}|\d{4})", re.I)


def _is_header_like(line: str) -> bool:
    """Determine if a line likely represents a header for an entry (job, project, education)."""
    if not line:
        return False
    if DATE_RE.search(line):
        return True
    if "@" in line or " at " in line.lower():
        return True
    # All-caps short lines (TITLE CASE too)
    words = line.split()
    if 1 <= len(words) <= 8 and (line.strip() == line.strip().upper() or any(w[0].isupper() for w in words)):
        return True
    return False


def _extract_dates_from_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    m = DATE_RE.search(line)
    if not m:
        return None, None
    span = m.group(0)
    # split on dash or 'to'
    parts = re.split(r"[-–—]|\bto\b", span, flags=re.I)
    parts = [p.strip().strip(".") for p in parts if p.strip()]
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def parse_experience_section(lines: List[str]) -> List[Dict]:
    """Parse an experience section into list of entries.

    Heuristics:
    - Detect header lines using `_is_header_like`.
    - Header may include title, company, dates. Try to split on '@' or ' at '.
    - Following lines that start with bullet markers or are short are treated as bullets.
    """
    entries: List[Dict] = []
    i = 0
    n = len(lines)
    bullet_marks = ("-", "•", "*", "·", "●", "▪", "►")

    while i < n:
        ln = lines[i].strip()
        if _is_header_like(ln):
            header = ln
            i += 1
            # collect additional header lines (company location on next line)
            while i < n and not lines[i].strip().startswith(bullet_marks) and not _is_header_like(lines[i]):
                # if the next line is short (<=6 words) and possibly part of header, include it
                if len(lines[i].split()) <= 8:
                    header = header + " | " + lines[i].strip()
                    i += 1
                else:
                    break

            # gather bullets
            bullets: List[str] = []
            while i < n and not _is_header_like(lines[i]):
                l = lines[i].strip()
                if not l:
                    i += 1
                    continue
                if l[0] in bullet_marks:
                    bullets.append(l.lstrip(''.join(bullet_marks)).strip())
                else:
                    # treat short lines or sentences following header as bullets
                    if len(l.split()) <= 30:
                        bullets.append(l)
                    else:
                        # long paragraph-like lines could also be bullets
                        bullets.append(l)
                i += 1

            # extract dates
            start_date, end_date = _extract_dates_from_line(header)

            title = None
            company = None
            location = None

            # split header on @ or ' at '
            if "@" in header:
                parts = header.split("@", 1)
                title = parts[0].strip()
                company = parts[1].strip()
            elif " at " in header.lower():
                parts = re.split(r"\s+at\s+", header, flags=re.I)
                if len(parts) >= 2:
                    title = parts[0].strip()
                    company = parts[1].strip()
            else:
                # try comma-separated (Title, Company)
                parts = [p.strip() for p in header.split(",") if p.strip()]
                if len(parts) >= 2:
                    title = parts[0]
                    company = parts[1]
                else:
                    # fallback: put whole header in title
                    title = header

            entry = {
                "title": title,
                "company": company,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "bullets": bullets,
                "raw_header": header,
            }
            entries.append(entry)
        else:
            # not header-like: skip or try to attach as a standalone bullet entry
            # gather until next header
            buffer_lines = []
            while i < n and not _is_header_like(lines[i]):
                buffer_lines.append(lines[i].strip())
                i += 1
            if buffer_lines:
                entries.append({
                    "title": None,
                    "company": None,
                    "location": None,
                    "start_date": None,
                    "end_date": None,
                    "bullets": buffer_lines,
                    "raw_header": None,
                })

    return entries


def parse_projects_section(lines: List[str]) -> List[Dict]:
    entries: List[Dict] = []
    i = 0
    n = len(lines)
    bullet_marks = ("-", "•", "*", "·", "●", "▪", "►")

    while i < n:
        ln = lines[i].strip()
        # treat a short line as project name
        if ln and (len(ln.split()) <= 10 or ln.endswith(":")):
            name = ln.rstrip(":")
            i += 1
            bullets: List[str] = []
            tech: List[str] = []
            role = None
            while i < n and not (lines[i].strip() and len(lines[i].split()) <= 10 and lines[i].strip() == lines[i].strip().upper()):
                l = lines[i].strip()
                if not l:
                    i += 1
                    continue
                if l[0] in bullet_marks:
                    bullets.append(l.lstrip(''.join(bullet_marks)).strip())
                else:
                    # look for tech: separated by | or ,
                    if "," in l or "|" in l:
                        tech += [t.strip() for t in re.split(r"[,|]", l) if t.strip()]
                    else:
                        # treat as a descriptive bullet
                        bullets.append(l)
                i += 1

            entries.append({"name": name, "role": role, "tech": tech, "bullets": bullets, "raw_header": ln})
        else:
            # fallback: aggregate lines until next short header-like line
            buffer = []
            while i < n and not (lines[i].strip() and len(lines[i].split()) <= 10 and lines[i].strip() == lines[i].strip().upper()):
                buffer.append(lines[i].strip())
                i += 1
            if buffer:
                entries.append({"name": None, "role": None, "tech": [], "bullets": buffer, "raw_header": None})

    return entries


def parse_education_section(lines: List[str]) -> List[Dict]:
    entries: List[Dict] = []
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue
        # often education entries are 1-2 lines: Degree, Institution, Year
        header = ln
        i += 1
        bullets: List[str] = []
        # capture following short lines as bullets (CGPA, honors)
        while i < n and len(lines[i].split()) <= 12 and not _is_header_like(lines[i]):
            l = lines[i].strip()
            if l:
                bullets.append(l)
            i += 1

        # attempt to split degree and institute
        degree = None
        institute = None
        # try comma separation
        parts = [p.strip() for p in header.split(",") if p.strip()]
        if len(parts) >= 2:
            degree = parts[0]
            institute = ", ".join(parts[1:])
        else:
            # try "Degree - Institute"
            if " - " in header:
                p = header.split(" - ", 1)
                degree = p[0].strip()
                institute = p[1].strip()
            else:
                degree = header

        entries.append({
            "degree": degree,
            "institute": institute,
            "bullets": bullets,
            "raw_header": header,
        })

    return entries


def parse_skills_section(lines: List[str]) -> List[str]:
    # join lines and split by common separators
    combined = " | ".join(lines)
    parts = [p.strip() for p in re.split(r"[,|;\n]", combined) if p.strip()]
    # normalize capitalization: title case each skill phrase
    skills = []
    for p in parts:
        # remove extra spaces
        s = re.sub(r"\s+", " ", p)
        # keep acronyms uppercase (e.g., SQL, AWS) by simple heuristic
        if s.upper() == s:
            skills.append(s)
        else:
            skills.append(s.title())
    # dedupe preserving order
    seen = set()
    out = []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def segment_sections(lines: List[str]) -> Dict[str, List[str]]:
    """Segment a flat list of lines into sections using header detection.

    Returns a dict mapping section_name -> list of lines in that section.
    Unknown/unlabeled content is stored under the key 'other'.
    """
    sections: Dict[str, List[str]] = {}
    current_section: str = "other"
    sections[current_section] = []

    for ln in lines:
        matched = _is_section_header(ln)
        if matched:
            current_section = matched
            if current_section not in sections:
                sections[current_section] = []
            continue

        sections.setdefault(current_section, []).append(ln)

    # Remove empty lists
    sections = {k: v for k, v in sections.items() if v}
    return sections


def remove_repeated_header_footer(blocks: List[List[str]]) -> List[List[str]]:
    """Detect and remove short lines that repeat across multiple blocks (likely headers/footers).

    Strategy: count occurrences of short lines (<=6 words). If a line appears in more than one block
    and it's short, remove all but the first occurrence.
    """
    counter = Counter()
    for block in blocks:
        seen = set()
        for ln in block:
            key = ln.strip()
            if len(key.split()) <= 6:
                seen.add(key)
        for k in seen:
            counter[k] += 1

    repeated = {k for k, v in counter.items() if v > 1}
    if not repeated:
        return blocks

    cleaned_blocks: List[List[str]] = []
    removed = set()
    for block in blocks:
        new_block = []
        for ln in block:
            key = ln.strip()
            if key in repeated:
                # keep the first time, skip subsequent times
                if key in removed:
                    continue
                removed.add(key)
            new_block.append(ln)
        if new_block:
            cleaned_blocks.append(new_block)

    return cleaned_blocks


def parse_resume_text(raw_text: str) -> Dict:
    """Top-level parser: take raw text and return structured dictionary.

    Returned dict keys:
    - name: Optional[str]
    - contact: dict with lists ('emails','phones','links')
    - blocks: List[List[str]] (blocks of lines)
    - lines: List[str] (flat, no empty lines)
    - sections: dict mapping section_name -> list[str]
    - raw_clean: cleaned text used for parsing
    """
    cleaned = _merge_hyphenated_words(raw_text)
    cleaned = _normalize_newlines(cleaned)

    blocks, flat_lines = preprocess_text_into_blocks(cleaned)
    # attempt to remove repeated headers/footers seen across blocks
    blocks = remove_repeated_header_footer(blocks)
    flat_lines = [ln for block in blocks for ln in block]

    name, contact, remaining = extract_header_info(flat_lines)
    sections = segment_sections(remaining)

    # Parse well-known sections into structured entries
    experience = []
    projects = []
    education = []
    skills = []
    other = {}

    if "experience" in sections:
        experience = parse_experience_section(sections["experience"])

    if "projects" in sections:
        projects = parse_projects_section(sections["projects"])

    if "education" in sections:
        education = parse_education_section(sections["education"])

    if "skills" in sections:
        skills = parse_skills_section(sections["skills"])

    # collect other small sections
    for k in ("certifications", "awards", "summary"):
        if k in sections:
            other[k] = sections[k]

    result = {
        "raw_text": raw_text,
        "raw_clean": cleaned,
        "name": name,
        "contact": contact,
        "blocks": blocks,
        "lines": flat_lines,
        "sections": sections,
        "experience": experience,
        "projects": projects,
        "education": education,
        "skills": skills,
        "other": other,
    }
    return result


if __name__ == "__main__":
    # quick smoke test when run directly
    sample = """
John Doe
Email: john.doe@example.com
Phone: +1 555-123-4567

EXPERIENCE
Senior Engineer at Acme Corp
- Built stuff

EDUCATION
BS Computer Science
"""
    import json

    out = parse_resume_text(sample)
    print(json.dumps(out, indent=2))
