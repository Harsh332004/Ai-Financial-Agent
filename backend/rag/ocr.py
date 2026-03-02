from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def _clean_ocr_noise(text: str) -> str:
    """Remove common OCR noise: repeated whitespace, null chars, weird symbols."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(file_path: str) -> str:
    """Extract text from a PDF or image file.

    Strategy:
    - PDFs: use pymupdf page.get_text() for digital text. If a page has
      fewer than 50 chars of text, render it at 300 DPI and pass through
      EasyOCR as a fallback.
    - Images (.png/.jpg/.jpeg/.tiff/.bmp/.webp): EasyOCR directly.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(file_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}:
        return _extract_image(file_path)
    else:
        logger.warning("Unsupported file type: %s", suffix)
        return ""


def _extract_pdf(file_path: str) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("pymupdf not installed — cannot extract PDF text")
        return ""

    texts: list[str] = []
    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc):
            digital_text = page.get_text()
            if len(digital_text.strip()) >= 50:
                texts.append(digital_text)
            else:
                # Scanned page — use EasyOCR on rendered image
                logger.debug("Page %d has sparse text, falling back to OCR", page_num)
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                ocr_text = _ocr_image_bytes(img_bytes)
                texts.append(ocr_text)
        doc.close()
    except Exception as e:
        logger.error("PDF extraction failed for %s: %s", file_path, e)

    combined = "\n\n".join(texts)
    return _clean_ocr_noise(combined)


def _extract_image(file_path: str) -> str:
    with open(file_path, "rb") as f:
        img_bytes = f.read()
    return _ocr_image_bytes(img_bytes)


def _ocr_image_bytes(img_bytes: bytes) -> str:
    """Run EasyOCR on raw image bytes."""
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        import io

        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_array = np.array(image)

        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(img_array, detail=0, paragraph=True)
        return _clean_ocr_noise("\n".join(results))
    except Exception as e:
        logger.error("EasyOCR failed: %s", e)
        return ""
