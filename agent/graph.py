import logging
import os
from ml.env import load_env

load_env()

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import (
    trigger_ml_pipeline,
    trigger_news_data_pipeline,
    query_knowledge_graph,
    check_system_health,
    get_kg_schema,
)

logger = logging.getLogger("agent_graph")

SYSTEM_PROMPT = """You are AirKube, an intelligent MLOps assistant.
Your goal is to help users manage ML pipelines, query the Knowledge Graph, and ensure system health.

Guidelines:
1. **Knowledge Graph**: You have access to a Neo4j Knowledge Graph with entities: Models, Experiments, Runs, Deployments.
   - Use `get_kg_schema` first if unsure about the data model before writing Cypher queries.
2. **System Health**: Use `check_system_health` to verify if the Inference API and components are running.
3. **Pipelines**: Trigger 'enhanced_ml_pipeline' via `trigger_ml_pipeline`, and 'news_data_pipeline' via `trigger_news_data_pipeline`.

Be concise and helpful. Always use tools when the user asks about system state, pipelines, or the knowledge graph.
"""

tools = [
    trigger_ml_pipeline,
    trigger_news_data_pipeline,
    query_knowledge_graph,
    check_system_health,
    get_kg_schema,
]

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("GEMINI_API_KEY not set — agent will fail on invocation.")

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    google_api_key=api_key,
    temperature=0,
)

llm_with_tools = llm.bind_tools(tools)


def call_model(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


tool_node = ToolNode(tools)

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

app = workflow.compile()
