import streamlit as st
import os
import json
from ml.env import load_env

load_env()

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agent.graph import app

# Page Config
st.set_page_config(page_title="AirKube Agent", page_icon="✈️", layout="wide")

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #fafbff 0%, #ffffff 100%);
        }
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(0, 0, 0, 0.06);
        }
        div[data-testid="stChatInput"] {
            bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("✈️ AirKube: Agentic MLOps Platform")
st.markdown("### Orchestrating ML Pipelines & Knowledge Graphs with AI")

# Sidebar for Configuration
with st.sidebar:
    st.header("Configuration")
    if os.getenv("GEMINI_API_KEY"):
        st.success("Gemini API key loaded from .env")
    else:
        st.warning("GEMINI_API_KEY not found in .env")

    view = st.radio(
        "View",
        ["Chat", "Knowledge Graph", "Extraction Playground"],
        index=0,
    )
    
    st.divider()
    st.subheader("System Health")
    if st.button("Check Health"):
        with st.spinner("Checking system status..."):
            from agent.tools import check_system_health
            status = check_system_health.invoke({})
            st.code(status, language="text")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

if view == "Chat":
    st.subheader("Agent Chat")
    st.caption("Ask about models, runs, pipeline triggers, or system state.")

    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.write(msg.content)

    user_input = st.chat_input("Ask about models, runs, or trigger pipelines...")

    if user_input:
        st.session_state.messages.append(HumanMessage(content=user_input))
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                inputs = {"messages": st.session_state.messages}
                final_state = app.invoke(inputs)
                response_msg = final_state["messages"][-1]
                st.write(response_msg.content)

                if isinstance(response_msg, AIMessage):
                    st.session_state.messages.append(response_msg)
                else:
                    st.session_state.messages.append(AIMessage(content=str(response_msg.content)))

elif view == "Knowledge Graph":
    st.subheader("Graph Explorer")
    st.info("Directly Query the Neo4j Database")
    
    cypher_query = st.text_area("Cypher Query", "MATCH (n) RETURN n LIMIT 25")
    if st.button("Run Query"):
        from agent.tools import query_knowledge_graph
        with st.spinner("Querying Neo4j..."):
            result = query_knowledge_graph.invoke({"query": cypher_query})
            st.write(result)

else:
    st.subheader("Test Knowledge Extraction")
    input_text = st.text_area("Input Text", """We trained ResNet50 v2 on dataset-coco-2024. 
The experiment 'Coco-Run-5' achieved 0.85 mAP. 
Deployed to cluster 'prod-us-west' with 5 replicas.""")
    
    if st.button("Extract Entities"):
        from ml.kg_extraction import extract_entities_from_text
        with st.spinner("Extracting with LLM..."):
            try:
                result = extract_entities_from_text(input_text)
                st.success("Extraction Complete!")
                st.json(result.dict())
            except Exception as e:
                st.error(f"Extraction failed: {e}")
