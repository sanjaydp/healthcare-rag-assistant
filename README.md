# Healthcare RAG Assistant

A domain-specific AI assistant that uses **Retrieval-Augmented Generation (RAG)** to answer questions over clinical healthcare documents and guidelines.  
The system provides **evidence-backed answers**, improving reliability and interpretability for healthcare-related queries.

---

## Architecture

```mermaid
flowchart TD
    A[User - Streamlit UI] --> B[FastAPI Backend /query]
    B --> C[LangGraph Workflow]

    C --> D[Query Rewrite]
    D --> E[Embedding Generation]

    E --> F[ChromaDB Vector Search]
    F --> G[Retrieved Documents]

    G --> H[Snippet Deduplication + Ranking]

    H --> I[LLM Answer Generation]
    I --> J[Evaluation Layer]

    J --> K[Support Status]
    J --> L[Confidence Score]

    K --> M[Final Response]
    L --> M

    M --> N[Streamlit UI Display]
```

---
