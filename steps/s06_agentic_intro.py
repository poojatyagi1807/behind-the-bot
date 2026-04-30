"""Step 6 — Agentic layer introduction."""
import streamlit as st
from config.content import STEP_INTROS, DOMAIN_TOOLS
from ui import render_topbar, render_step_header, render_enterprise_note, render_nav

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s06_agentic_intro"][domain]
    tools = DOMAIN_TOOLS.get(domain, [])

    render_step_header("🤖", "Welcome to the Agentic Layer",
        "This is where the AI stops reading and starts acting.")

    st.markdown(f"""
<div style="background:var(--color-background-secondary);border-left:3px solid #1D9E75;
border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:16px;
font-size:13px;color:var(--color-text-secondary);line-height:1.6;font-style:italic">
{content["thinking"]}
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Most people think AI works like this:**")
        st.code("Question in → Magic happens → Answer out", language=None)

        st.markdown("**What actually happens:**")
        st.code("""Question in
     ↓
AI makes a plan
     ↓
AI fetches information it needs
     ↓
AI reasons over what it found
     ↓
  Confident enough?
  NO → go back, fetch more
  YES ↓
Answer out""", language=None)

    with col2:
        st.markdown("**Three sub-steps inside this loop:**")
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:14px">
  <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:0.5px solid var(--color-border-tertiary)">
    <div style="font-size:12px;font-weight:500;color:var(--color-text-primary)">🔍 RAG Retrieval</div>
    <div style="font-size:11px;color:var(--color-text-tertiary)">Finds relevant policy from knowledge base</div>
  </div>
  <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:0.5px solid var(--color-border-tertiary)">
    <div style="font-size:12px;font-weight:500;color:var(--color-text-primary)">🔧 Tool Execution</div>
    <div style="font-size:11px;color:var(--color-text-tertiary)">Calls: {" · ".join(tools)}</div>
  </div>
  <div>
    <div style="font-size:12px;font-weight:500;color:var(--color-text-primary)">🧠 LLM Reasoning</div>
    <div style="font-size:11px;color:var(--color-text-tertiary)">Reasons over all gathered data to produce answer</div>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("**Why it matters:**")
        st.markdown(f"""
<div style="font-size:12px;color:var(--color-text-secondary);line-height:1.6;
padding:10px 14px;background:var(--color-background-secondary);border-radius:8px">
{content["why"]}
</div>
""", unsafe_allow_html=True)

    # MCP section
    st.markdown("---")
    st.markdown("**🏢 How enterprises connect tools — MCP Servers**")
    st.markdown("""
In production, an AI agent doesn't directly call your database. That would be a security nightmare.

Instead, enterprises use **MCP — Model Context Protocol** (open-sourced by Anthropic in November 2024). 
Think of it as a standardised plug socket for AI tools.
""")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.code("""
AI Agent
    │ speaks MCP
    ▼
MCP Server (secure middleware)
    │           │           │
    ▼           ▼           ▼
Booking DB   CRM         Payment
             Salesforce  Processor
""", language=None)

    with col_b:
        st.markdown("""
The AI never touches your database directly. It asks the MCP server, which authenticates, fetches, 
and returns **only what the AI is permitted to see**.

**Real MCP tool call — JSON-RPC format:**
""")
        st.code("""{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "lookup_booking",
    "arguments": {
      "booking_id": "BK-29471",
      "user_id": "sarah_m_4821"
    }
  }
}""", language="json")
        st.caption("Source: Official MCP protocol spec — modelcontextprotocol.io")

    render_enterprise_note(
        "Anthropic open-sourced MCP in November 2024. Companies like Salesforce, Atlassian, "
        "and GitHub have already built MCP servers — meaning an AI agent can now connect to "
        "Jira, Slack, or Salesforce using a standardised interface without custom integration "
        "work for each one. OpenAI and Google DeepMind both adopted MCP in 2025."
    )

    render_nav(back=True, next_label="Next: RAG Retrieval →")
