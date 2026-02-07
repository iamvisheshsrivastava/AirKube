import streamlit as st
import os
import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agent.graph import app

# Page Config
st.set_page_config(page_title="AirKube Agent", page_icon="✈️", layout="wide")

st.title("✈️ AirKube: Agentic MLOps Platform")
st.markdown("### Orchestrating ML Pipelines & Knowledge Graphs with AI")

# Sidebar for Configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    st.divider()
    st.subheader("System Health")
    if st.button("Check Health"):
        with st.spinner("Checking system status..."):
            from agent.tools import check_system_health
            status = check_system_health()
            st.code(status, language="text")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tabbed Interface
tab_chat, tab_kg, tab_extract = st.tabs(["💬 Agent Chat", "🕸️ Knowledge Graph", "📝 Extraction Playground"])

# --- TAB 1: Agent Chat ---
with tab_chat:
    # Display Chat History
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.write(msg.content)
    
    # User Input
    user_input = st.chat_input("Ask about models, runs, or trigger pipelines...")
    
    if user_input:
        # Add user message to state
        st.session_state.messages.append(HumanMessage(content=user_input))
        with st.chat_message("user"):
            st.write(user_input)
            
        # Run Agent
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Prepare inputs for the graph
                # We need to pass the history effectively.
                # The 'app' expects 'messages' in the state.
                inputs = {"messages": st.session_state.messages}
                
                # Run the graph
                # We use stream or invoke. Invoke returns the final state.
                final_state = app.invoke(inputs)
                
                # Get the last message (response)
                response_msg = final_state["messages"][-1]
                
                # Display response
                st.write(response_msg.content)
                
                # Update session state with the full conversation including tool calls if any
                # But for simplicity in display, we just append the AI response
                # Note: LangGraph state management is complex. We might just append the AI Message.
                if isinstance(response_msg, AIMessage):
                    st.session_state.messages.append(response_msg)
                else:
                    # Fallback for other message types
                    st.session_state.messages.append(AIMessage(content=str(response_msg.content)))

# --- TAB 2: Knowledge Graph ---
with tab_kg:
    st.subheader("Graph Explorer")
    st.info("Directly Query the Neo4j Database")
    
    cypher_query = st.text_area("Cypher Query", "MATCH (n) RETURN n LIMIT 25")
    if st.button("Run Query"):
        from agent.tools import query_knowledge_graph
        with st.spinner("Querying Neo4j..."):
            result = query_knowledge_graph(cypher_query)
            st.write(result)

# --- TAB 3: Extraction Playground ---
with tab_extract:
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
