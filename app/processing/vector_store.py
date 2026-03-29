from langchain_community.vectorstores import Chroma
from app.processing.embeddings import get_embedding_model
from app.core.config import settings


def get_vector_store():
    embedding_model = get_embedding_model()

    vectordb = Chroma(
        persist_directory=settings.chroma_persist_dir,
        embedding_function=embedding_model
    )

    return vectordb


def reset_vector_store():
    vectordb = get_vector_store()
    try:
        vectordb.delete_collection()
    except Exception:
        pass