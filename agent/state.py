from typing import TypedDict, Annotated, Sequence, Union
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """
    The state of the agent in the LangGraph.
    
    Attributes:
        messages: A list of messages (Human, AI, System, Function) representing the conversation history.
                  We use `operator.add` to append new messages to the list rather than overwriting.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
