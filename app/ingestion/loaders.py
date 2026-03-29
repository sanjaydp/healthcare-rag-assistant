from pypdf import PdfReader
from typing import List
from app.core.logger import get_logger

logger = get_logger(__name__)


def load_pdf(file_path: str) -> List[str]:
    """
    Load PDF and return list of page texts
    """
    reader = PdfReader(file_path)
    pages_text = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages_text.append(text)
        else:
            logger.warning(f"No text found on page {i}")

    logger.info(f"Loaded {len(pages_text)} pages from {file_path}")
    return pages_text