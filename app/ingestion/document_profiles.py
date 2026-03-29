import re


def apply_document_specific_fixes(text: str, source: str) -> str:
    source_lower = source.lower()

    # CDC TBI discharge instructions specific fixes
    if "tbi_patient_instructions" in source_lower:
        text = re.sub(r"\bnot to away\b", "not go away", text)
        text = re.sub(r"\bordecreased\b", "or decreased", text)
        text = re.sub(r"\bMore information on mild TBI and concussion.*$", "", text)

    return text