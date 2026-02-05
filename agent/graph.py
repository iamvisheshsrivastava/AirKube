import json
import logging
import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor

from agent.state import AgentState
from agent.tools import trigger_ml_pipeline, query_knowledge_graph, check_system_health, get_kg_schema

logger = logging.getLogger("agent_graph")

# 1. Define Tools
tools = [trigger_ml_pipeline, query_knowledge_graph, check_system_health, get_kg_schema]
tool_executor = ToolExecutor(tools)

# 2. Define Model
# We gracefully handle missing API keys for demo purposes
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("OPENAI_API_KEY not found. Agent will fail if invoked.")
    # For robust code, we might want a mock, but let's assume the user will provide it.
    
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, streaming=True)
model = llm.bind_tools(tools)

# 3. Define Nodes

SYSTEM_PROMPT = """You are AirKube, an intelligent MLOps assistant. 
Your goal is to help users manage ML pipelines, query the Knowledge Graph, and ensure system health.

Guidelines:
1. **Knowledge Graph**: You have access to a Neo4j Knowledge Graph containing entities like Models, Experiments, Runs, and Deployments.
   - ALWAYS use `get_kg_schema` first if you are unsure about the data model or before writing complex Cypher queries.
   - The schema is NOT medical (diseases/drugs); it is MLOps focused.
2. **System Health**: Use `check_system_health` to verify if the Inference API and other components are running.
3. **Pipelines**: You can trigger the 'enhanced_ml_pipeline' using `trigger_ml_pipeline`.

Be concise and helpful.
"""

def call_model(state: AgentState):
    messages = state['messages']
    # Prepend system message to the context sent to the LLM
    # We do NOT add this to the global state history to avoid duplication, 
    # just to the local call context.
    prompt_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = model.invoke(prompt_messages)
    return {"messages": [response]}

def call_tool(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    
    tool_inputs = []
    
    # We iterate over tool calls in the last message
    if hasattr(last_message, "tool_calls"):
        for tool_call in last_message.tool_calls:
            action = tool_executor.invoke(tool_call)
            tool_message = ToolMessage(
                tool_call_id=tool_call['id'],
                content=str(action),
                name=tool_call['name']
            )
            tool_inputs.append(tool_message)
            
    return {"messages": tool_inputs}

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
workflow.add_node("action", call_tool)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END
    }
)

workflow.add_edge("action", "agent")

app = workflow.compile()
