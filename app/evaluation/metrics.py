from app.evaluation.dataset import EVAL_DATASET
from app.generation.rag_chain import generate_answer


def keyword_match_score(answer: str, expected_keywords: list[str]) -> float:
    answer_lower = answer.lower()
    matches = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return matches / len(expected_keywords) if expected_keywords else 0.0


def source_page_hit(retrieved_chunks: list[dict], expected_pages: list[int]) -> bool:
    retrieved_pages = {
        chunk.get("metadata", {}).get("page")
        for chunk in retrieved_chunks
    }
    return any(page in retrieved_pages for page in expected_pages)


def run_evaluation():
    results = []

    for item in EVAL_DATASET:
        result = generate_answer(item["question"])

        answer = result.get("answer", "")
        retrieved_chunks = result.get("retrieved_chunks", [])

        keyword_score = keyword_match_score(
            answer,
            item["expected_answer_contains"]
        )

        source_hit = source_page_hit(
            retrieved_chunks,
            item["expected_source_pages"]
        )

        results.append(
            {
                "question": item["question"],
                "answer": answer,
                "keyword_score": round(keyword_score, 2),
                "source_hit": source_hit
            }
        )

    return results