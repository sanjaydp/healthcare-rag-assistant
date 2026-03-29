from app.processing.vector_store import get_vector_store


def get_retriever(selected_source: str | None = None):
    vectordb = get_vector_store()

    search_kwargs = {
        "k": 6,
        "fetch_k": 20,
    }

    if selected_source and selected_source != "All Documents":
        search_kwargs["filter"] = {"source": selected_source}

    return vectordb.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs
    )