import re


def clean_text(text: str) -> str:
    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r", "\n")

    # Join words broken by newline inside a word
    text = re.sub(r"([A-Za-z])\n([a-z])", r"\1\2", text)

    # Convert remaining single newlines to spaces
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Put bullets on their own lines
    text = re.sub(r"\s*•\s*", "\n• ", text)

    # Add sentence breaks
    text = re.sub(r"\.\s+", ".\n", text)

    # Collapse repeated newlines/spaces
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)

    return text.strip()


def clean_pages(pages: list[str]) -> list[str]:
    cleaned = []
    for page in pages:
        page = clean_text(page)
        if page:
            cleaned.append(page)
    return cleaned