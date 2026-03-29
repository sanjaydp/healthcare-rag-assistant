import uuid
import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Clinical Guideline Assistant",
    layout="wide"
)


def deduplicate_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    unique = []

    for src in sources:
        key = (src.get("source"), src.get("page"))
        if key not in seen:
            seen.add(key)
            unique.append(src)

    return unique


def deduplicate_snippets(snippets: list[dict]) -> list[dict]:
    seen = set()
    unique = []

    for snippet in snippets:
        text = (snippet.get("text") or "").strip()
        source = snippet.get("source")
        page = snippet.get("page")
        key = (text, source, page)

        if text and key not in seen:
            seen.add(key)
            unique.append(snippet)

    return unique


def deduplicate_chunks(chunks: list[dict]) -> list[dict]:
    seen = set()
    unique = []

    for chunk in chunks:
        text = (chunk.get("content") or "").strip()
        meta = chunk.get("metadata", {})
        source = meta.get("source")
        page = meta.get("page")
        key = (text, source, page)

        if text and key not in seen:
            seen.add(key)
            unique.append(chunk)

    return unique


def render_status_card(title: str, value: str):
    value_upper = (value or "UNKNOWN").upper()

    if value_upper in {"SUPPORTED", "HIGH"}:
        bg_color = "#e8f7ee"
        border_color = "#2e8b57"
        text_color = "#1f5133"
        icon = "✅"
    elif value_upper in {"PARTIALLY_SUPPORTED", "MEDIUM"}:
        bg_color = "#fff8e6"
        border_color = "#d4a72c"
        text_color = "#7a5d00"
        icon = "🟡"
    elif value_upper in {"NOT_SUPPORTED", "LOW"}:
        bg_color = "#fdecec"
        border_color = "#c0392b"
        text_color = "#7b241c"
        icon = "❌"
    else:
        bg_color = "#f4f4f4"
        border_color = "#999999"
        text_color = "#333333"
        icon = "ℹ️"

    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            border-left: 6px solid {border_color};
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 8px;
            min-height: 110px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        ">
            <div style="
                font-size: 0.95rem;
                color: #444;
                margin-bottom: 8px;
                font-weight: 600;
            ">
                {title}
            </div>
            <div style="
                font-size: 1.7rem;
                font-weight: 800;
                color: {text_color};
                line-height: 1.2;
            ">
                {icon} {value_upper}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_answer_card(answer: str):
    st.markdown(
        f"""
        <div style="
            background-color: #f9fafb;
            border-left: 6px solid #4a90e2;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 15px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        ">
            <div style="
                font-size: 1rem;
                color: #333;
                line-height: 1.6;
            ">
                {answer}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def get_snippet_label(index: int, text: str) -> str:
    text_lower = (text or "").lower()

    if index == 0:
        return "🔹 Key Recommendation"
    if "should" in text_lower or "recommend" in text_lower:
        return "🔹 Recommended Action"
    if "avoid" in text_lower or "contraindicated" in text_lower:
        return "🔹 Contraindication"
    if "risk" in text_lower or "warning" in text_lower:
        return "🔹 Risk / Warning"
    if "follow" in text_lower or "monitor" in text_lower:
        return "🔹 Follow-up Guidance"

    return "🔹 Supporting Evidence"


if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

st.title("Clinical Guideline Assistant")
st.caption("Ask questions about clinical recommendations, contraindications, risks, and follow-up guidance.")

top_left, top_right = st.columns([4, 1])

with top_left:
    uploaded_file = st.file_uploader(
        "Upload a PDF or text file",
        type=["pdf", "txt"]
    )

with top_right:
    st.write("")
    st.write("")
    if st.button("New Conversation"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.success("Started a new conversation.")

if uploaded_file is not None:
    st.info(f"Selected file: {uploaded_file.name}")

    if st.button("Upload Document"):
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type
            )
        }

        response = requests.post(f"{API_BASE_URL}/upload/", files=files)

        if response.status_code == 200:
            result = response.json()

            if "error" in result:
                st.error(result["error"])
            else:
                if uploaded_file.name not in st.session_state.uploaded_files:
                    st.session_state.uploaded_files.append(uploaded_file.name)

                st.success(f"Uploaded: {uploaded_file.name}")

                with st.expander("Upload Summary", expanded=False):
                    st.json(result)
        else:
            st.error("Upload failed.")
            st.text(response.text)

document_options = ["All Documents"] + st.session_state.uploaded_files
selected_source = st.selectbox(
    "Choose document scope",
    options=document_options
)

question = st.text_input(
    "Ask a clinical question:",
    placeholder="e.g., What is the recommended treatment? What are contraindications?"
)

if st.button("Submit Question"):
    if not st.session_state.uploaded_files:
        st.warning("Please upload at least one document first.")
    elif question.strip():
        payload = {
            "question": question,
            "thread_id": st.session_state.thread_id,
            "selected_source": selected_source
        }

        response = requests.post(
            f"{API_BASE_URL}/query/",
            json=payload
        )

        if response.status_code == 200:
            result = response.json()

            answer = result.get("answer", "No answer returned.")
            support_status = result.get("support_status", "UNKNOWN")
            confidence = result.get("confidence", "UNKNOWN")

            sources = deduplicate_sources(result.get("sources", []))
            snippets = deduplicate_snippets(result.get("support_snippets", []))
            chunks = deduplicate_chunks(result.get("retrieved_chunks", []))

            refusal_text = "The answer is not available in the provided clinical guidelines."

            st.subheader("Answer")
            render_answer_card(answer)

            if answer.strip() == refusal_text:
                st.warning("⚠️ Not enough evidence found in the clinical guidelines to answer this question reliably.")

            st.subheader("Answer Quality")

            q1, q2 = st.columns(2)
            with q1:
                render_status_card("Support Status", support_status)
            with q2:
                render_status_card("Confidence", confidence)

            st.subheader("Supporting Snippets")
            if snippets:
                for i, snippet in enumerate(snippets):
                    st.markdown(f"**{get_snippet_label(i, snippet.get('text', ''))}**")
                    st.caption(
                        f"Source: {snippet.get('source', 'unknown')} | "
                        f"Page: {snippet.get('page', 'unknown')}"
                    )
                    st.write(snippet.get("text", ""))
                    st.markdown("---")
            else:
                st.info("No supporting snippets extracted.")

            st.subheader("Sources")
            if sources:
                for src in sources:
                    st.write(
                        f"• {src.get('source', 'unknown')} | "
                        f"Page: {src.get('page', 'unknown')}"
                    )
            else:
                st.info("No sources available.")

            with st.expander("Show Retrieval Details", expanded=False):
                if chunks:
                    for i, chunk in enumerate(chunks, start=1):
                        st.markdown(f"**Chunk {i}**")
                        meta = chunk.get("metadata", {})
                        st.caption(
                            f"Source: {meta.get('source', 'unknown')} | "
                            f"Page: {meta.get('page', 'unknown')}"
                        )
                        st.write(chunk.get("content", ""))
                        st.markdown("---")
                else:
                    st.info("No retrieved chunks available.")

            st.session_state.chat_history.append(
                {
                    "question": question,
                    "answer": answer
                }
            )

        else:
            st.error("Query failed.")
            st.text(response.text)
    else:
        st.warning("Please enter a question.")

if st.session_state.chat_history:
    with st.expander("Conversation History", expanded=True):
        for i, turn in enumerate(st.session_state.chat_history, start=1):
            st.markdown(f"**Q{i}:** {turn['question']}")
            st.markdown(f"**A{i}:** {turn['answer']}")
            st.markdown("---")

st.caption(f"Thread ID: {st.session_state.thread_id}")