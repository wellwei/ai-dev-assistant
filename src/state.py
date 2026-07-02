from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    task: str
    messages: Annotated[Sequence[BaseMessage], operator.add]
    plan: str
    code: str
    test_result: str
    review_feedback: str
    approved: bool
    human_feedback: str
    current_step: str