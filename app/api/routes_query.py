from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.graph import graph
from app.evaluation.metrics import run_evaluation

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    thread_id: str
    selected_source: Optional[str] = None


def re_match_dash_bullet(line: str) -> bool:
    return line.startswith("-") or line.startswith("–") or line.startswith("—")


def remove_leading_dash(line: str) -> str:
    if line and line[0] in {"-", "–", "—"}:
        return line[1:].strip()
    return line.strip()


def is_summary_question(question: str) -> bool:
    question = question.lower().strip()

    keywords = [
        "what is this document about",
        "what is this about",
        "summary",
        "overview",
        "summarize",
        "summarise",
        "explain this document",
        "describe this document",
        "key recommendations",
        "summarize this guideline",
        "summarise this guideline",
        "what does this guideline say",
    ]

    return any(k in question for k in keywords)


def is_treatment_or_action_question(question: str) -> bool:
    question = question.lower().strip()

    keywords = [
        "what is recommended",
        "what should",
        "when should",
        "when is",
        "how should",
        "how is",
        "what does the guideline recommend",
        "recommended treatment",
        "treatment",
        "management",
        "follow-up",
        "monitoring",
        "contraindication",
        "contraindications",
        "should statin",
        "should ezetimibe",
        "should pcsk9",
        "should inclisiran",
        "should therapy",
        "when to",
        "when do",
    ]

    return any(k in question for k in keywords)


def format_clinical_answer(text: str, question: str) -> str:
    if not text:
        return ""

    refusal_text = "The answer is not available in the provided clinical guidelines."
    if text.strip() == refusal_text:
        return refusal_text

    text = text.replace("**", "")
    text = text.replace("*", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("#", "")

    lines = text.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re_match_dash_bullet(line):
            line = "• " + remove_leading_dash(line)

        line = " ".join(line.split())
        cleaned.append(line)

    cleaned_text = "\n".join(cleaned).strip()

    # Only prepend Recommendation for treatment/action questions
    if (
        is_treatment_or_action_question(question)
        and not is_summary_question(question)
        and not cleaned_text.lower().startswith("recommendation:")
    ):
        cleaned_text = f"Recommendation:\n\n{cleaned_text}"

    return cleaned_text


@router.post("/")
def ask_question(payload: QueryRequest):
    result = graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": payload.question,
                }
            ],
            "selected_source": payload.selected_source,
            "rewritten_query": "",
            "retrieved_chunks": [],
            "sources": [],
            "confidence": "",
            "support_status": "",
            "support_snippets": [],
        },
        config={"configurable": {"thread_id": payload.thread_id}},
    )

    final_answer = ""
    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            final_answer = last_message.get("content", "")
        else:
            final_answer = str(last_message)

    final_answer = format_clinical_answer(final_answer, payload.question)

    return {
        "question": payload.question,
        "answer": final_answer,
        "confidence": result.get("confidence", "UNKNOWN"),
        "support_status": result.get("support_status", "UNKNOWN"),
        "support_snippets": result.get("support_snippets", []),
        "sources": result.get("sources", []),
        "retrieved_chunks": result.get("retrieved_chunks", []),
    }


@router.get("/evaluate")
def evaluate_rag():
    return {
        "results": run_evaluation()
    }