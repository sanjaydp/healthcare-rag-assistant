from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT
from app.retrieval.retriever import get_retriever


def build_rag_chain(selected_source: str | None = None):
    retriever = get_retriever(selected_source=selected_source)

    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                "Conversation History:\n{chat_history}\n\n"
                "Question: {question}\n\n"
                "Context:\n{context}\n\n"
                "Answer only from the provided context. Use conversation history only to understand follow-up questions."
            ),
        ]
    )

    return retriever, prompt, llm


def format_chat_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return "No previous conversation."

    lines = []
    for turn in chat_history:
        q = turn.get("question", "")
        a = turn.get("answer", "")
        lines.append(f"User: {q}")
        lines.append(f"Assistant: {a}")
    return "\n".join(lines)


def generate_answer(question: str, chat_history: list[dict] | None = None, selected_source: str | None = None):
    chat_history = chat_history or []

    retriever, prompt, llm = build_rag_chain(selected_source=selected_source)

    docs = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in docs])

    messages = prompt.invoke(
        {
            "question": question,
            "context": context,
            "chat_history": format_chat_history(chat_history)
        }
    )

    response = llm.invoke(messages)

    return {
        "question": question,
        "answer": response.content,
        "sources": [
            {
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page")
            }
            for doc in docs
        ],
        "retrieved_chunks": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in docs
        ],
    }