"""Safe PDF text extraction with an OCR fallback for scanned pages."""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


MAX_PAGES = int(os.getenv("PDF_MAX_PAGES", "40"))
MAX_TOTAL_CHARS = int(os.getenv("PDF_MAX_TOTAL_CHARS", "180000"))
MAX_PAGE_CHARS = int(os.getenv("PDF_MAX_PAGE_CHARS", "20000"))
MIN_TEXT_LAYER_CHARS = int(os.getenv("PDF_MIN_TEXT_CHARS", "40"))
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "rus+eng")


@dataclass(frozen=True)
class ExtractedPage:
    page: int
    text: str
    method: str


class PdfExtractionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def clean_text(value: str) -> str:
    """Normalize PDF artefacts while preserving paragraph boundaries."""
    text = value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[\t\u00a0 ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


def _repeated_margin_lines(texts: list[str]) -> set[str]:
    candidates: Counter[str] = Counter()
    for text in texts:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in {*lines[:2], *lines[-2:]}:
            if 3 <= len(line) <= 120:
                candidates[line] += 1
    threshold = max(3, (len(texts) + 1) // 2)
    return {line for line, count in candidates.items() if count >= threshold}


def _remove_margins(text: str, repeated: set[str]) -> str:
    return "\n".join(line for line in text.splitlines() if line.strip() not in repeated).strip()


def _ocr_pages(raw: bytes, page_numbers: list[int]) -> dict[int, str]:
    """OCR only pages whose text layer is absent or clearly unusable."""
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - depends on optional runtime packages
        raise PdfExtractionError("OCR_UNAVAILABLE", "OCR dependencies are not installed") from exc

    result: dict[int, str] = {}
    try:
        document = fitz.open(stream=raw, filetype="pdf")
        for page_number in page_numbers:
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            result[page_number] = clean_text(
                pytesseract.image_to_string(image, lang=OCR_LANGUAGES, config="--psm 6")
            )
    except PdfExtractionError:
        raise
    except Exception as exc:
        raise PdfExtractionError("OCR_FAILED", "The scanned PDF could not be recognized") from exc
    return result


def extract_pdf_pages(raw: bytes) -> list[ExtractedPage]:
    """Extract a bounded, cleaned set of pages suitable for a grounded prompt."""
    try:
        reader = PdfReader(BytesIO(raw), strict=False)
    except Exception as exc:
        raise PdfExtractionError("PDF_PARSE_FAILED", "The file is not a readable PDF") from exc
    if reader.is_encrypted:
        try:
            if reader.decrypt("") == 0:
                raise PdfExtractionError("PDF_PASSWORD_PROTECTED", "Password-protected PDF is unsupported")
        except PdfExtractionError:
            raise
        except Exception as exc:
            raise PdfExtractionError("PDF_PASSWORD_PROTECTED", "Password-protected PDF is unsupported") from exc
    if not reader.pages:
        raise PdfExtractionError("PDF_HAS_NO_PAGES", "The PDF has no pages")
    if len(reader.pages) > MAX_PAGES:
        raise PdfExtractionError("PDF_TOO_MANY_PAGES", f"The PDF contains more than {MAX_PAGES} pages")

    texts: list[str] = []
    try:
        for page in reader.pages:
            texts.append(clean_text(page.extract_text() or ""))
    except Exception as exc:
        raise PdfExtractionError("PDF_PARSE_FAILED", "The PDF text layer could not be read") from exc

    # Preserve vector equation geometry where a page is predominantly math.
    # Ordinary prose and text-less scans keep the established extraction path.
    math_pages = set()
    try:
        import fitz
        from backend.pdf_math import math_page_text
        with fitz.open(stream=raw, filetype="pdf") as layout_document:
            for index, layout_page in enumerate(layout_document):
                structured = math_page_text(layout_page)
                if structured:
                    texts[index] = clean_text(structured)
                    math_pages.add(index + 1)
    except (ImportError, RuntimeError, ValueError):
        # Optional layout support must not disable readable ordinary PDFs.
        pass

    needs_ocr = [index for index, text in enumerate(texts, start=1) if len(text) < MIN_TEXT_LAYER_CHARS]
    if needs_ocr:
        try:
            recognized = _ocr_pages(raw, needs_ocr)
        except PdfExtractionError:
            # A partially scanned PDF remains useful if other pages have a
            # readable text layer. Reject only when OCR is the sole option.
            if not any(len(text) >= MIN_TEXT_LAYER_CHARS for text in texts):
                raise
            recognized = {}
        for page_number, text in recognized.items():
            if len(text) >= MIN_TEXT_LAYER_CHARS:
                texts[page_number - 1] = text

    repeated = _repeated_margin_lines(texts)
    pages: list[ExtractedPage] = []
    total = 0
    for page_number, text in enumerate(texts, start=1):
        cleaned = _remove_margins(text, repeated)[:MAX_PAGE_CHARS].strip()
        if len(cleaned) < 10:
            continue
        remaining = MAX_TOTAL_CHARS - total
        if remaining <= 0:
            break
        cleaned = cleaned[:remaining]
        method = "ocr" if page_number in needs_ocr else "math_layout" if page_number in math_pages else "text_layer"
        pages.append(ExtractedPage(page=page_number, text=cleaned, method=method))
        total += len(cleaned)

    if not pages:
        raise PdfExtractionError("PDF_HAS_NO_READABLE_TEXT", "No readable text was found after OCR")
    return pages
