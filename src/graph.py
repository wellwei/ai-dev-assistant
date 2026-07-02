import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from src.state import AgentState
from src.nodes.planner import planner
from src.nodes.coder import coder
from src.nodes.tester import tester
from src.nodes.reviewer import reviewer

def extract_task(state: AgentState):
    """从 messages 中提取用户输入作为 task"""
    messages = state.get("messages", [])
    
    # 找最后一条人类消息
    task = state.get("task", "")
    if not task and messages:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) or getattr(msg, "type", None) == "human":
                task = msg.content
                break
    
    return {
        "task": task,
        "messages": messages,
        "current_step": "task_extracted"
    }

def should_continue(state: AgentState):
    if state.get("approved"):
        return "end"
    return "revise"

def create_graph():
    builder = StateGraph(AgentState)
    
    # 添加节点
    builder.add_node("extract_task", extract_task)
    builder.add_node("planner", planner)
    builder.add_node("coder", coder)
    builder.add_node("tester", tester)
    builder.add_node("reviewer", reviewer)
    
    # 入口先提取 task
    builder.set_entry_point("extract_task")
    builder.add_edge("extract_task", "planner")
    builder.add_edge("planner", "coder")
    builder.add_edge("coder", "tester")
    builder.add_edge("tester", "reviewer")
    
    builder.add_conditional_edges(
        "reviewer",
        should_continue,
        {"end": END, "revise": "coder"}
    )
    
    return builder.compile(checkpointer=InMemorySaver())