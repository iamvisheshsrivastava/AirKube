import logging
import os
from ml.env import load_env

load_env()

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
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

## Knowledge Graph Schema (Neo4j)
Node labels and properties:
- Model      (id, name, version, framework, description)
- Experiment (id, name, status, created_at)
- Run        (id, name, status, metrics, parameters)
- Deployment (id, name, cluster, image, replicas, status)

Relationships — use EXACTLY these names:
- (:Run)-[:BELONGS_TO]->(:Experiment)
- (:Model)-[:PRODUCED_BY]->(:Run)
- (:Deployment)-[:SERVES]->(:Model)

Example queries:
- All deployed models:  MATCH (d:Deployment)-[:SERVES]->(m:Model) RETURN d.name, m.name, m.version
- Experiments & runs:   MATCH (r:Run)-[:BELONGS_TO]->(e:Experiment) RETURN e.name, r.name, r.status
- Full pipeline trace:  MATCH (d)-[:SERVES]->(m)-[:PRODUCED_BY]->(r)-[:BELONGS_TO]->(e) RETURN d.name,m.name,r.name,e.name

## Guidelines
1. Always use `query_knowledge_graph` with correct Cypher when asked about models, runs, experiments, or deployments.
2. Use `check_system_health` to verify API and component status.
3. Use `trigger_ml_pipeline` or `trigger_news_data_pipeline` to start pipelines.
4. Be concise. Show results clearly.
"""

tools = [
    trigger_ml_pipeline,
    trigger_news_data_pipeline,
    query_knowledge_graph,
    check_system_health,
    get_kg_schema,
]

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    logger.warning("OPENROUTER_API_KEY not set — agent will fail on invocation.")

llm = ChatOpenAI(
    model=os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.6"),
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
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
