from fastapi import APIRouter, UploadFile, File
import os

from app.core.config import settings
from app.ingestion.loaders import load_pdf
from app.ingestion.clean_text import clean_pages
from app.ingestion.document_profiles import apply_document_specific_fixes
from app.processing.chunker import chunk_text
from app.processing.vector_store import get_vector_store

router = APIRouter()


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    os.makedirs(settings.raw_data_dir, exist_ok=True)

    file_path = os.path.join(settings.raw_data_dir, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    pages = load_pdf(file_path)

    if not pages:
        return {
            "error": "No text found in PDF. This may be a scanned document."
        }

    cleaned_pages = clean_pages(pages)

    profile_fixed_pages = [
        apply_document_specific_fixes(page, file.filename)
        for page in cleaned_pages
    ]

    chunks = chunk_text(profile_fixed_pages, source=file.filename)

    if not chunks:
        return {
            "error": "No text chunks created from document."
        }

    vectordb = get_vector_store()
    vectordb.add_documents(chunks)

    return {
        "filename": file.filename,
        "pages_loaded": len(pages),
        "chunks_created": len(chunks),
        "sample_chunk": chunks[0].page_content if chunks else None
    }