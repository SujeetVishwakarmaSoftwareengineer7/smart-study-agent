"""
File Processor — Extract text from PDF, TXT, and image files.
All content is treated as untrusted reference data only.
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 12000  # chars to extract per file


def extract_text(file_path: str, original_filename: str = "") -> str:
    """
    Extract readable text from a supported file type.
    Returns clean text string.
    """
    ext = Path(file_path).suffix.lower().lstrip(".")

    if ext == "pdf":
        return _extract_pdf(file_path)
    elif ext == "txt":
        return _extract_txt(file_path)
    elif ext in ("png", "jpg", "jpeg", "webp"):
        return _extract_image(file_path)
    else:
        logger.warning("Unsupported file extension: %s", ext)
        return ""


def _extract_pdf(file_path: str) -> str:
    try:
        import PyPDF2
        text_parts = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
                    if sum(len(p) for p in text_parts) >= MAX_TEXT_LENGTH:
                        break
                except Exception as page_err:
                    logger.warning("Could not extract page %d: %s", page_num, page_err)
        raw = "\n".join(text_parts)
        return _clean_text(raw)[:MAX_TEXT_LENGTH]
    except ImportError:
        logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
        return "[PDF extraction unavailable — PyPDF2 not installed]"
    except Exception as exc:
        logger.error("PDF extraction error: %s", exc)
        return ""


def _extract_txt(file_path: str) -> str:
    try:
        # Try UTF-8 first, fall back to latin-1
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read(MAX_TEXT_LENGTH * 2)
                return _clean_text(content)[:MAX_TEXT_LENGTH]
            except UnicodeDecodeError:
                continue
        return ""
    except Exception as exc:
        logger.error("TXT extraction error: %s", exc)
        return ""


def _extract_image(file_path: str) -> str:
    """Attempt OCR on image files using pytesseract."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(file_path)
        # Resize if too large (OCR performance)
        max_dim = 2000
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size)
        text = pytesseract.image_to_string(img)
        return _clean_text(text)[:MAX_TEXT_LENGTH]
    except ImportError:
        logger.warning("Pillow or pytesseract not installed — image OCR unavailable")
        return "[Image OCR unavailable — pytesseract not installed. Please install Tesseract OCR and pytesseract.]"
    except Exception as exc:
        logger.error("Image OCR error: %s", exc)
        return f"[Could not extract text from image: {exc}]"


def _clean_text(text: str) -> str:
    """Remove control characters, normalise whitespace."""
    if not text:
        return ""
    # Remove null bytes and non-printable chars (keep newlines, tabs)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    # Normalise multiple blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Normalise multiple spaces
    text = re.sub(r" {4,}", "   ", text)
    return text.strip()
