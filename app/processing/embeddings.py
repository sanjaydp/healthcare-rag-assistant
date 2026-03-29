from langchain_openai import OpenAIEmbeddings
from app.core.config import settings


def get_embedding_model():
    return OpenAIEmbeddings(
        model=settings.embedding_model
    )