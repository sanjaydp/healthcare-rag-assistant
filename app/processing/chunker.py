from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(pages: list[str], source: str = "uploaded_file"):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n• ", "\n", ". ", " ", ""]
    )

    chunks = []

    for page_num, page_text in enumerate(pages, start=1):
        if not page_text.strip():
            continue

        split_chunks = splitter.split_text(page_text)

        for chunk in split_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            chunks.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source": source,
                        "page": page_num
                    }
                )
            )

    return chunks