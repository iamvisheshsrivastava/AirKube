import json
import logging
import os
from ml.env import load_env

load_env()

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
import google.generativeai as genai

from agent.state import AgentState
from agent.tools import trigger_ml_pipeline, trigger_news_data_pipeline, query_knowledge_graph, check_system_health, get_kg_schema

logger = logging.getLogger("agent_graph")

# 1. Define Tools
tools = [trigger_ml_pipeline, trigger_news_data_pipeline, query_knowledge_graph, check_system_health, get_kg_schema]

# 2. Define Model
# We gracefully handle missing API keys for demo purposes
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning("GEMINI_API_KEY not found. Agent will fail if invoked.")
    # For robust code, we might want a mock, but let's assume the user will provide it.

genai.configure(api_key=api_key)
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

# 3. Define Nodes

SYSTEM_PROMPT = """You are AirKube, an intelligent MLOps assistant. 
Your goal is to help users manage ML pipelines, query the Knowledge Graph, and ensure system health.

Guidelines:
1. **Knowledge Graph**: You have access to a Neo4j Knowledge Graph containing entities like Models, Experiments, Runs, and Deployments.
   - ALWAYS use `get_kg_schema` first if you are unsure about the data model or before writing complex Cypher queries.
   - The schema is NOT medical (diseases/drugs); it is MLOps focused.
2. **System Health**: Use `check_system_health` to verify if the Inference API and other components are running.
3. **Pipelines**: You can trigger the 'enhanced_ml_pipeline' using `trigger_ml_pipeline`, and the 'news_data_pipeline' using `trigger_news_data_pipeline`.

Be concise and helpful.
"""

def call_model(state: AgentState):
    messages = state['messages']
    try:
        conversation = []
        for message in messages:
            role = "user"
            if message.__class__.__name__.lower().startswith("ai"):
                role = "assistant"
            conversation.append(f"{role}: {message.content}")

        prompt = f"{SYSTEM_PROMPT}\n\nConversation so far:\n" + "\n".join(conversation) + "\n\nRespond to the latest user message only."
        response = model.generate_content(prompt)
        response_text = getattr(response, "text", None) or str(response)
        return {"messages": [AIMessage(content=response_text)]}
    except Exception as error:
        logger.error("Gemini call failed: %s", error)
        return {"messages": [AIMessage(content=f"Gemini error: {error}")]}

# 4. Define Logic

def should_continue(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    return "end"

# 5. Build Graph

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)

workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

app = workflow.compile()
