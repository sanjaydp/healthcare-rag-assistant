from typing import Annotated, Optional, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


from typing import List, Dict, TypedDict


class GraphState(TypedDict):
    messages: List[Dict]  # ✅ JSON safe
    selected_source: str
    rewritten_query: str
    retrieved_chunks: List[str]
    sources: List[str]
    confidence: str
    support_status: str
    support_snippets: List[str]