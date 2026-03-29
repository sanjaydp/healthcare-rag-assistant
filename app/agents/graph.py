import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, END, StateGraph

from app.agents.nodes import (
    rewrite_query_node,
    retrieve_node,
    answer_node,
    evaluate_answer_node,
)
from app.agents.state import GraphState
from app.core.config import settings


def build_graph():
    os.makedirs(os.path.dirname(settings.memory_db_path), exist_ok=True)

    conn = sqlite3.connect(settings.memory_db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    builder = StateGraph(GraphState)

    builder.add_node("rewrite", rewrite_query_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("answer", answer_node)
    builder.add_node("evaluate", evaluate_answer_node)

    builder.add_edge(START, "rewrite")
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("retrieve", "answer")
    builder.add_edge("answer", "evaluate")
    builder.add_edge("evaluate", END)

    return builder.compile(checkpointer=checkpointer)


graph = build_graph()