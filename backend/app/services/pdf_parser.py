import re
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract and clean text from PDF bytes using pdfplumber."""
    try:
        import pdfplumber
        text_pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
                logger.debug(f"Processed page {i + 1}/{len(pdf.pages)}")
        return "\n\n".join(text_pages)
    except ImportError:
        logger.warning("pdfplumber not available, trying PyMuPDF")
        return _extract_with_pymupdf(file_bytes)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Failed to parse PDF: {str(e)}")


def _extract_with_pymupdf(file_bytes: bytes) -> str:
    """Fallback PDF extraction using PyMuPDF (fitz)."""
    try:
        import fitz
        text_pages = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                text_pages.append(page.get_text())
        return "\n\n".join(text_pages)
    except Exception as e:
        raise ValueError(f"PDF extraction failed with all methods: {str(e)}")


def clean_and_structure_text(raw_text: str) -> str:
    """
    Clean and structure the extracted resume text:
    - Remove redundant whitespace and special characters
    - Normalize line breaks
    - Preserve meaningful structure
    """
    if not raw_text:
        return ""

    # Normalize unicode spaces and special chars
    text = raw_text.replace("\u00a0", " ").replace("\u200b", "")

    # Remove non-printable characters except newlines and tabs
    text = re.sub(r"[^\x09\x0a\x0d\x20-\x7e\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", "", text)

    # Collapse multiple spaces into one
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize multiple newlines (keep max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Trim leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]

    # Remove completely empty lines at the start/end of sections
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if line == "":
            if not prev_empty:
                cleaned_lines.append(line)
            prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False

    return "\n".join(cleaned_lines).strip()


def segment_resume_sections(text: str) -> dict:
    """
    Attempt to segment resume into logical sections for better AI processing.
    Returns a dict with section names as keys.
    """
    section_keywords = {
        "basic_info": ["个人信息", "基本信息", "personal information", "contact"],
        "education": ["教育背景", "教育经历", "学历", "education"],
        "experience": ["工作经历", "工作经验", "work experience", "employment"],
        "skills": ["技能", "专业技能", "skills", "abilities"],
        "projects": ["项目经历", "项目经验", "projects"],
        "summary": ["个人简介", "自我评价", "summary", "objective"],
    }

    sections = {"full_text": text}
    text_lower = text.lower()

    for section, keywords in section_keywords.items():
        for kw in keywords:
            if kw in text_lower or kw in text:
                # Find approximate section boundaries
                idx = text_lower.find(kw) if kw in text_lower else text.find(kw)
                if idx != -1:
                    # Extract ~500 chars from that section
                    sections[section] = text[idx : idx + 800].strip()
                    break

    return sections
