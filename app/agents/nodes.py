import re
from typing import List, Dict, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import GraphState
from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT
from app.processing.embeddings import get_embedding_model
from app.processing.vector_store import get_vector_store
from app.retrieval.retriever import get_retriever


def get_latest_user_question(messages: List[Dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def deduplicate_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []

    for src in sources:
        key = (src.get("source"), src.get("page"))
        if key not in seen:
            seen.add(key)
            unique.append(src)

    return unique


def deduplicate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []

    for chunk in chunks:
        text = (chunk.get("content") or "").strip()
        metadata = chunk.get("metadata", {})
        key = (
            text,
            metadata.get("source"),
            metadata.get("page")
        )

        if text and key not in seen:
            seen.add(key)
            unique.append(chunk)

    return unique


def deduplicate_snippets(snippets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []

    for snippet in snippets:
        text = (snippet.get("text") or "").strip()
        key = (
            text,
            snippet.get("source"),
            snippet.get("page")
        )

        if text and key not in seen:
            seen.add(key)
            unique.append(snippet)

    return unique


def is_summary_question(question: str) -> bool:
    question = question.lower().strip()

    keywords = [
        "what is this document about",
        "what is this about",
        "what is this guideline about",
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


def is_broad_management_question(question: str) -> bool:
    question = question.lower().strip()

    keywords = [
        "what does the guideline recommend for",
        "management of",
        "recommend for diabetes",
        "recommend for ascvd",
        "recommend for ckd",
        "recommend for hiv",
        "recommend for hypertriglyceridemia",
        "recommend for severe hypercholesterolemia",
    ]

    return any(k in question for k in keywords)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def normalize_answer_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("**", "")
    text = text.replace("*", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("#", "")

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r"^[-–—]\s*", line):
            line = "• " + re.sub(r"^[-–—]\s*", "", line).strip()
        elif re.match(r"^[•]\s*", line):
            line = "• " + re.sub(r"^[•]\s*", "", line).strip()

        line = re.sub(r"\s+", " ", line)
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def build_clinical_prompt(context: str, question: str) -> str:
    return f"""
You are a Clinical Guideline Assistant.

Answer the question using ONLY the provided clinical guideline context.

Formatting rules:
- Return a short, clinician-friendly answer.
- Prefer compact bullet points.
- Use clear recommendation language such as:
  Recommend, Consider, Reasonable, Not recommended
- Include numeric thresholds when available.
- Do not use markdown like ** or *.
- Do not write long paragraphs.
- Do not repeat the question.

If the answer is not supported by the context, say exactly:
The answer is not available in the provided clinical guidelines.

Context:
{context}

Question:
{question}

Answer:
"""


def build_clinical_summary_prompt(context: str, question: str) -> str:
    return f"""
You are a Clinical Guideline Assistant.

Summarize the key clinical guidance from the document.

Formatting rules:
- Use 4 to 6 short bullet points.
- Focus on:
  - Main topic
  - Key recommendations
  - Contraindications or precautions
  - Monitoring or follow-up
- Prefer overview content such as abstract, scope, key messages, and major recommendations.
- Do not use markdown like ** or *.
- Keep the summary concise and clinically useful.

If the summary is not supported by the context, say exactly:
The answer is not available in the provided clinical guidelines.

Context:
{context}

Question:
{question}

Answer:
"""


def rewrite_query_node(state: GraphState):
    messages = state.get("messages", [])
    latest_question = get_latest_user_question(messages)

    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0
    )

    conversation_text = "\n".join(
        f"{m.get('role', 'unknown')}: {m.get('content', '')}"
        for m in messages
    )

    rewrite_prompt = f"""
Rewrite the following question into a standalone clinical question using the conversation history.

Rules:
- Keep the meaning exactly the same.
- If the question is already standalone, return it unchanged.
- Do not make it broader or vaguer.
- Preserve clinical intent.

Conversation:
{conversation_text}

Question:
{latest_question}

Rewritten standalone question:
"""

    response = llm.invoke(rewrite_prompt)
    rewritten = response.content.strip()

    if not rewritten:
        rewritten = latest_question

    return {
        "rewritten_query": rewritten
    }


def retrieve_summary_chunks(query: str, selected_source: str | None):
    vectordb = get_vector_store()

    filters = None
    if selected_source and selected_source != "All Documents":
        filters = {"source": selected_source}

    priority_queries = [
        query,
        "abstract scope purpose of this clinical guideline",
        "top take-home messages what is new summary guideline",
        "introduction scope management of dyslipidemia",
    ]

    all_docs = []
    for q in priority_queries:
        try:
            docs = vectordb.similarity_search(
                q,
                k=8,
                filter=filters
            )
            all_docs.extend(docs)
        except Exception:
            continue

    # prioritize early pages and summary-like text
    scored = []
    for doc in all_docs:
        content = (doc.page_content or "").lower()
        page = doc.metadata.get("page", 9999)

        score = 0
        if page <= 10:
            score += 5
        if "abstract" in content:
            score += 4
        if "scope" in content:
            score += 4
        if "what is new" in content:
            score += 4
        if "top take-home messages" in content:
            score += 4
        if "management of dyslipidemia" in content:
            score += 3
        if "guideline" in content:
            score += 2

        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = []
    seen = set()
    for _, doc in scored:
        key = (
            doc.page_content.strip(),
            doc.metadata.get("source"),
            doc.metadata.get("page")
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(doc)
        if len(selected) >= 8:
            break

    return selected


def retrieve_node(state: GraphState):
    selected_source = state.get("selected_source")
    query = state.get("rewritten_query", "")
    messages = state.get("messages", [])
    latest_question = get_latest_user_question(messages)

    print(f"\n=== RETRIEVAL QUERY ===\n{query}\n")
    print(f"\n=== SELECTED SOURCE ===\n{selected_source}\n")

    docs = []

    if is_summary_question(latest_question):
        docs = retrieve_summary_chunks(query, selected_source)
    else:
        retriever = get_retriever(selected_source=selected_source)
        docs = retriever.invoke(query)

        if is_broad_management_question(latest_question):
            try:
                vectordb = get_vector_store()
                filters = None
                if selected_source and selected_source != "All Documents":
                    filters = {"source": selected_source}
                broad_docs = vectordb.similarity_search(query, k=10, filter=filters)
                docs.extend(broad_docs)
            except Exception:
                pass

    print(f"\n=== RETRIEVED DOC COUNT ===\n{len(docs)}\n")

    retrieved_chunks = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in docs
    ]

    sources = [
        {
            "source": doc.metadata.get("source"),
            "page": doc.metadata.get("page")
        }
        for doc in docs
    ]

    retrieved_chunks = deduplicate_chunks(retrieved_chunks)
    sources = deduplicate_sources(sources)

    return {
        "retrieved_chunks": retrieved_chunks,
        "sources": sources
    }


def answer_node(state: GraphState):
    messages = state.get("messages", [])
    retrieved_chunks = state.get("retrieved_chunks", [])
    rewritten_query = state.get("rewritten_query", "")

    context = "\n\n".join(
        chunk.get("content", "")
        for chunk in retrieved_chunks
    )

    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0
    )

    latest_question = get_latest_user_question(messages)

    if is_summary_question(latest_question):
        prompt = build_clinical_summary_prompt(
            context=context,
            question=rewritten_query or latest_question
        )
    else:
        prompt = build_clinical_prompt(
            context=context,
            question=rewritten_query or latest_question
        )

    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])

    cleaned_answer = normalize_answer_text(response.content)

    return {
        "messages": [
            {
                "role": "assistant",
                "content": cleaned_answer
            }
        ]
    }


def split_into_sentences(text: str) -> list[str]:
    if not text:
        return []

    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def extract_support_snippets(
    retrieved_chunks: List[Dict[str, Any]],
    answer: str,
    question: str,
    top_k: int = 3
):
    embedding_model = get_embedding_model()

    candidates = []

    question_embedding = embedding_model.embed_query(question)
    answer_embedding = embedding_model.embed_query(answer)

    for chunk in retrieved_chunks:
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})

        sentences = split_into_sentences(content)

        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence.split()) < 4:
                continue
            clean_sentences.append(sentence)

        if not clean_sentences:
            continue

        sentence_embeddings = embedding_model.embed_documents(clean_sentences)

        for sentence, sentence_embedding in zip(clean_sentences, sentence_embeddings):
            q_score = cosine_similarity(question_embedding, sentence_embedding)
            a_score = cosine_similarity(answer_embedding, sentence_embedding)

            score = (0.6 * q_score) + (0.4 * a_score)

            word_count = len(sentence.split())
            if 8 <= word_count <= 35:
                score += 0.03
            elif word_count < 5:
                score -= 0.05

            if re.search(r"\b\d+\b", sentence):
                score += 0.02

            candidates.append(
                {
                    "text": sentence,
                    "score": score,
                    "source": metadata.get("source"),
                    "page": metadata.get("page"),
                    "embedding": sentence_embedding
                }
            )

    candidates.sort(key=lambda x: x["score"], reverse=True)

    selected = []
    selected_embeddings = []

    for item in candidates:
        is_duplicate = False
        for existing_emb in selected_embeddings:
            sim = cosine_similarity(existing_emb, item["embedding"])
            if sim > 0.90:
                is_duplicate = True
                break

        if is_duplicate:
            continue

        selected.append(item)
        selected_embeddings.append(item["embedding"])

        if len(selected) >= top_k:
            break

    final_results = []
    for item in selected:
        final_results.append(
            {
                "text": item["text"],
                "source": item["source"],
                "page": item["page"]
            }
        )

    return deduplicate_snippets(final_results)


def evaluate_answer_node(state: GraphState):
    messages = state.get("messages", [])
    retrieved_chunks = state.get("retrieved_chunks", [])

    final_answer = ""
    latest_question = ""

    for message in reversed(messages):
        if message.get("role") == "assistant" and not final_answer:
            final_answer = message.get("content", "")
        if message.get("role") == "user" and not latest_question:
            latest_question = message.get("content", "")
        if final_answer and latest_question:
            break

    refusal_text = "the answer is not available in the provided clinical guidelines."

    if final_answer.strip().lower() == refusal_text:
        return {
            "confidence": "HIGH",
            "support_status": "NOT_SUPPORTED",
            "support_snippets": []
        }

    support_snippets = extract_support_snippets(
        retrieved_chunks=retrieved_chunks,
        answer=final_answer,
        question=latest_question,
        top_k=3
    )
    support_snippets = deduplicate_snippets(support_snippets)

    if is_summary_question(latest_question):
        if retrieved_chunks and support_snippets:
            return {
                "confidence": "MEDIUM",
                "support_status": "SUPPORTED",
                "support_snippets": support_snippets
            }
        elif retrieved_chunks:
            return {
                "confidence": "MEDIUM",
                "support_status": "PARTIALLY_SUPPORTED",
                "support_snippets": support_snippets
            }
        else:
            return {
                "confidence": "LOW",
                "support_status": "NOT_SUPPORTED",
                "support_snippets": []
            }

    if is_broad_management_question(latest_question):
        if retrieved_chunks and support_snippets:
            return {
                "confidence": "MEDIUM",
                "support_status": "SUPPORTED",
                "support_snippets": support_snippets
            }
        elif retrieved_chunks:
            return {
                "confidence": "MEDIUM",
                "support_status": "PARTIALLY_SUPPORTED",
                "support_snippets": support_snippets
            }

    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0
    )

    context = "\n\n".join(
        chunk.get("content", "")
        for chunk in retrieved_chunks
    )

    evaluation_prompt = f"""
You are evaluating whether an answer is supported by retrieved clinical guideline context.

Retrieved Context:
{context}

Answer:
{final_answer}

Classify the answer using these rules:
- SUPPORTED: Answer is clearly grounded in the retrieved context
- PARTIALLY_SUPPORTED: Some of the answer is supported, but some parts are not clearly grounded
- NOT_SUPPORTED: The answer is mostly unsupported or missing from context

Also assign confidence:
- HIGH
- MEDIUM
- LOW

Return ONLY in this exact format:
SUPPORT_STATUS: <SUPPORTED or PARTIALLY_SUPPORTED or NOT_SUPPORTED>
CONFIDENCE: <HIGH or MEDIUM or LOW>
"""

    response = llm.invoke(evaluation_prompt)
    text = response.content.strip()

    support_status = "UNKNOWN"
    confidence = "UNKNOWN"

    for line in text.splitlines():
        if line.startswith("SUPPORT_STATUS:"):
            support_status = line.replace("SUPPORT_STATUS:", "").strip().upper()
        elif line.startswith("CONFIDENCE:"):
            confidence = line.replace("CONFIDENCE:", "").strip().upper()

    if support_status == "NOT_SUPPORTED":
        confidence = "LOW"
    elif support_status == "PARTIALLY_SUPPORTED" and confidence == "HIGH":
        confidence = "MEDIUM"

    return {
        "confidence": confidence,
        "support_status": support_status,
        "support_snippets": support_snippets
    }