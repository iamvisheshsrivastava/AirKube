import streamlit as st
import os
import logging
from ml.env import load_env

load_env()

import ddtrace.auto  # noqa: F401
from ddtrace import tracer
from langchain_core.messages import HumanMessage, AIMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("airkube.dashboard")

st.set_page_config(
    page_title="AirKube · MLOps Platform",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #f1f5f9; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] label { color: #cbd5e1 !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(99,102,241,0.3) !important;
    border-color: #6366f1 !important;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 60%, #6366f1 100%);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 20px;
    color: white;
    box-shadow: 0 4px 24px rgba(79,70,229,0.3);
}
.hero h1 { margin: 0 0 6px 0; font-size: 26px; font-weight: 700; letter-spacing: -0.5px; }
.hero p  { margin: 0; opacity: 0.8; font-size: 14px; }
.hero-badges { margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }
.badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 500;
}

/* ── Suggestion chips ── */
div[data-testid="column"] .stButton > button {
    background: white !important;
    border: 1.5px solid #e2e8f0 !important;
    color: #475569 !important;
    border-radius: 999px !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    padding: 5px 14px !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
    white-space: normal !important;
    line-height: 1.4 !important;
    min-height: 38px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
div[data-testid="column"] .stButton > button:hover {
    background: #6366f1 !important;
    border-color: #6366f1 !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(99,102,241,0.3) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: white;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #e2e8f0;
    gap: 2px;
    margin-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
    color: #64748b !important;
}
.stTabs [aria-selected="true"] {
    background: #6366f1 !important;
    color: white !important;
}

/* ── Chat container ── */
.chat-wrap {
    background: white;
    border-radius: 14px;
    padding: 20px;
    border: 1px solid #e2e8f0;
    margin-bottom: 12px;
    min-height: 320px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 10px !important;
    border: 1.5px solid #e2e8f0 !important;
    font-size: 14px !important;
    background: white !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
}

/* ── Primary button ── */
.stButton [kind="primary"],
button[kind="primary"] {
    background: #6366f1 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ── Section labels ── */
.section-label {
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 8px;
}

/* ── KG example pills ── */
.stSelectbox > div > div {
    border-radius: 10px !important;
    border: 1.5px solid #e2e8f0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding: 24px 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 16px;'>
        <div style='font-size:20px; font-weight:700; color:white; letter-spacing:-0.5px;'>✈️ AirKube</div>
        <div style='font-size:11.5px; color:#64748b; margin-top:3px;'>Agentic MLOps Platform</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="color:#475569!important;padding:0 4px">Navigation</div>', unsafe_allow_html=True)
    view = st.radio(
        "",
        ["💬  Chat", "🔗  Knowledge Graph", "🧪  Extraction"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown('<div class="section-label" style="color:#475569!important;padding:0 4px">Connections</div>', unsafe_allow_html=True)

    gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
    neo4j_uri = os.getenv("NEO4J_URI", "")
    neo4j_ok = "databases.neo4j.io" in neo4j_uri or ("localhost" in neo4j_uri)

    st.markdown(
        f"{'🟢' if gemini_ok else '🔴'} Gemini {'connected' if gemini_ok else 'not configured'}"
    )
    st.markdown(
        f"{'🟢' if neo4j_ok else '🔴'} Neo4j {'Aura' if 'databases.neo4j.io' in neo4j_uri else 'local' if neo4j_ok else 'not configured'}"
    )
    news_ok = bool(os.getenv("NEWS_API_KEY"))
    st.markdown(f"{'🟢' if news_ok else '🟡'} NewsAPI {'connected' if news_ok else 'not set'}")

    st.divider()
    st.markdown('<div class="section-label" style="color:#475569!important;padding:0 4px">System Health</div>', unsafe_allow_html=True)
    if st.button("🔍  Run Health Check", use_container_width=True):
        with st.spinner("Checking..."):
            from agent.tools import check_system_health
            result = check_system_health.invoke({})
            for part in result.split(" | "):
                if "[OK]" in part:
                    st.success(part.replace("[OK] ", ""), icon="✅")
                elif "[ERR]" in part:
                    st.error(part.replace("[ERR] ", ""), icon="❌")
                else:
                    st.warning(part.replace("[WARN] ", ""), icon="⚠️")

    if st.session_state.messages:
        st.divider()
        if st.button("🗑️  Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>✈️ AirKube MLOps Platform</h1>
    <p>Orchestrating ML pipelines & Knowledge Graphs with an agentic AI copilot</p>
    <div class="hero-badges">
        <span class="badge">LangGraph Agent</span>
        <span class="badge">Neo4j Knowledge Graph</span>
        <span class="badge">Gemini 2.5 Flash</span>
        <span class="badge">Apache Airflow</span>
        <span class="badge">Datadog APM</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Lazy imports ───────────────────────────────────────────────────────────────
from agent.graph import app

# ── Views ──────────────────────────────────────────────────────────────────────
if view == "💬  Chat":

    st.markdown('<div class="section-label">Quick actions</div>', unsafe_allow_html=True)
    suggestions = [
        "What models are deployed?",
        "Check system health",
        "Show experiments & runs",
        "Trigger the ML pipeline",
        "Show active deployments",
        "Get the KG schema",
    ]
    cols = st.columns(3)
    for i, s in enumerate(suggestions):
        if cols[i % 3].button(s, key=f"chip_{i}"):
            st.session_state.pending_input = s
            st.rerun()

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    # Chat history
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user", avatar="👤"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage) and msg.content:
            with st.chat_message("assistant", avatar="✈️"):
                st.write(msg.content)

    # Resolve input — chip click takes priority
    user_input = st.chat_input("Ask about models, pipelines, deployments, or system state…")
    if st.session_state.pending_input:
        user_input = st.session_state.pending_input
        st.session_state.pending_input = None

    if user_input:
        st.session_state.messages.append(HumanMessage(content=user_input))
        with st.chat_message("user", avatar="👤"):
            st.write(user_input)

        with st.chat_message("assistant", avatar="✈️"):
            with st.spinner("Thinking…"):
                with tracer.trace("dashboard.agent_invoke", service="airkube-dashboard"):
                    final_state = app.invoke({"messages": st.session_state.messages})
                ai_msgs = [
                    m for m in final_state["messages"]
                    if isinstance(m, AIMessage) and m.content
                ]
                response = ai_msgs[-1] if ai_msgs else AIMessage(content="No response generated.")
                logger.info("Agent responded to user query")
                st.write(response.content)
                st.session_state.messages.append(response)

elif view == "🔗  Knowledge Graph":
    st.markdown("### Knowledge Graph Explorer")
    st.caption("Query your Neo4j Aura instance directly with Cypher")

    EXAMPLE_QUERIES = {
        "All nodes (overview)":
            "MATCH (n) RETURN n LIMIT 25",
        "Deployed models":
            "MATCH (d:Deployment)-[:SERVES]->(m:Model) RETURN d.name AS deployment, m.name AS model, m.version",
        "Experiments & runs":
            "MATCH (r:Run)-[:BELONGS_TO]->(e:Experiment) RETURN e.name AS experiment, r.name AS run, r.status",
        "Full pipeline trace":
            "MATCH (d:Deployment)-[:SERVES]->(m:Model)-[:PRODUCED_BY]->(r:Run)-[:BELONGS_TO]->(e:Experiment) RETURN d.name, m.name, r.name, e.name",
        "Failed runs":
            "MATCH (r:Run) WHERE r.status = 'failed' RETURN r.name, r.metrics",
    }

    st.markdown('<div class="section-label">Example queries</div>', unsafe_allow_html=True)
    ecols = st.columns(len(EXAMPLE_QUERIES))
    selected_q = None
    for i, (label, q) in enumerate(EXAMPLE_QUERIES.items()):
        if ecols[i].button(label, key=f"eq_{i}"):
            selected_q = q

    cypher = st.text_area(
        "Cypher Query",
        value=selected_q if selected_q else "MATCH (n) RETURN n LIMIT 25",
        height=100,
        label_visibility="collapsed",
        placeholder="Write your Cypher query here…",
    )

    if st.button("▶  Run Query", type="primary"):
        from agent.tools import query_knowledge_graph
        with st.spinner("Querying Neo4j…"):
            result = query_knowledge_graph.invoke({"query": cypher})
        if result == "No results found.":
            st.info("No results returned. The graph may be empty or the query matched nothing.", icon="ℹ️")
        elif result.startswith("Error"):
            st.error(result, icon="❌")
        else:
            st.success("Query completed", icon="✅")
            st.code(result, language="json")

else:  # Extraction Playground
    st.markdown("### Knowledge Extraction Playground")
    st.caption("Paste any text — Gemini extracts MLOps entities and structures them into the KG schema")

    SAMPLE = """We trained ResNet50 v2 on dataset-coco-2024.
The experiment 'Coco-Run-5' achieved 0.85 mAP.
Deployed to cluster 'prod-us-west' with 5 replicas."""

    input_text = st.text_area(
        "Input text",
        value=SAMPLE,
        height=140,
        label_visibility="collapsed",
        placeholder="Paste any text describing an ML experiment, model, or deployment…",
    )

    if st.button("⚡  Extract Entities", type="primary"):
        from ml.kg_extraction import extract_entities_from_text
        with st.spinner("Extracting with Gemini…"):
            try:
                result = extract_entities_from_text(input_text)
                st.success("Extraction complete!", icon="✅")
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.markdown("**Structured output**")
                    st.json(result.dict())
                with col2:
                    st.markdown("**Summary**")
                    for key, val in result.dict().items():
                        if val:
                            st.markdown(f"**{key.replace('_', ' ').title()}**")
                            st.markdown(f"> {val}")
            except Exception as e:
                st.error(f"Extraction failed: {e}", icon="❌")
