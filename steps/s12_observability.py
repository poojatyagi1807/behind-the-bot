"""Step 12 — Observability trace and system architecture."""
import streamlit as st
from datetime import datetime
from config.content import STEP_INTROS
from ui import render_topbar, render_step_header, render_thinking_card, render_enterprise_note, render_risk_table, render_nav
from state import get_result

RISKS = [
    {
        "risk": "No observability",
        "example": "Guardrail starts misfiring — blocks 20% of legitimate queries — nobody notices for 3 days",
        "mitigation": "Real-time monitoring — alert when guardrail fire rate exceeds baseline by more than 2x",
    },
    {
        "risk": "PII in logs",
        "example": "User messages stored in plain text logs — GDPR violation, security risk",
        "mitigation": "PII scrubbing pipeline — anonymise before logging, never store raw user messages",
    },
    {
        "risk": "Slow-burn degradation",
        "example": "RAG confidence scores gradually dropping over 6 weeks — no single alarm fires",
        "mitigation": "Trend monitoring — alert on week-over-week degradation not just absolute thresholds",
    },
    {
        "risk": "No feedback loop",
        "example": "Conversations logged but never analysed — same failures repeat for months",
        "mitigation": "Dedicated AI ops role — someone owns the trace data and acts on it weekly, not quarterly",
    },
]

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s12_observability"][domain]

    render_step_header("📊", "Observability Layer — The Trace",
        "Every decision logged. Every pattern surfaced.")

    render_thinking_card(content["thinking"])

    # Gather all results
    intent = get_result("intent") or {}
    rag = get_result("rag") or {}
    tools = get_result("tools") or {}
    reasoning = get_result("reasoning") or {}
    guardrails = get_result("output_guardrails") or {}
    profile = st.session_state.profile or {}

    total_latency = (
        intent.get("processing_time_ms", 142) +
        rag.get("processing_time_ms", 89) +
        tools.get("total_latency", 202) +
        reasoning.get("processing_time_ms", 1840) +
        guardrails.get("processing_time_ms", 270)
    )

    # Full trace
    st.markdown("**The full conversation trace:**")
    st.code(f"""CONVERSATION TRACE — SESSION-{profile.get("id","X")}-{datetime.now().strftime("%H%M%S")}
Timestamp         {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC
Domain            {domain.upper()}
User              {profile.get("name","Unknown")} (anonymised)

── LAYER OUTPUTS ──────────────────────────────────

Authentication
  Trust score     {profile.get("trust_score","—")}/100
  Risk flag       {"High — multiple disputes" if profile.get("past_disputes",0) > 3 else "None"}
  Bot detection   Human confirmed

Input guardrails
  Status          Clean
  Latency         35ms

Intent
  Primary         {intent.get("primary_intent","—")} ({intent.get("primary_confidence",0):.0%})
  Secondary       {intent.get("secondary_intent") or "None"}
  Sentiment       {intent.get("sentiment","—")}
  Urgency         {intent.get("urgency","—")}
  Routing         {intent.get("routing_suggestion","—")}
  Latency         {intent.get("processing_time_ms","—")}ms

RAG
  Chunks total    {rag.get("total_chunks","—")}
  Retrieved       {rag.get("top_k","—")}
  Best score      {rag.get("best_score",0):.2f}
  Low confidence  {"Yes ⚠️" if rag.get("low_confidence") else "No"}
  Latency         {rag.get("processing_time_ms","—")}ms

Tools
  Calls           {len(tools.get("calls",[]))}
  Failed          {sum(1 for c in tools.get("calls",[]) if not c.get("success",True))}
  Latency         {tools.get("total_latency","—")}ms

Reasoning
  Tokens          ~{reasoning.get("total_tokens",0):,}
  Grounded        {"Yes" if reasoning.get("grounded") else "No ⚠️"}
  Latency         {reasoning.get("processing_time_ms","—")}ms

Output guardrails
  Status          {guardrails.get("overall_status","—")}
  Summary         {guardrails.get("summary","—")}
  Latency         {guardrails.get("processing_time_ms","—")}ms

── OUTCOME ─────────────────────────────────────────

Resolution        AI response delivered
Total latency     {total_latency}ms
Est. cost         ~${total_latency * 0.0000015:.4f}
""", language=None)

    # What this feeds into
    st.markdown("**What this trace feeds into:**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
<div style="padding:10px;background:var(--color-background-secondary);border-radius:8px;
font-size:11px;color:var(--color-text-secondary);line-height:1.6;text-align:center">
<div style="font-size:13px;margin-bottom:4px">📡</div>
<strong>Real-time monitoring</strong><br>Is anything broken right now?
</div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
<div style="padding:10px;background:var(--color-background-secondary);border-radius:8px;
font-size:11px;color:var(--color-text-secondary);line-height:1.6;text-align:center">
<div style="font-size:13px;margin-bottom:4px">📈</div>
<strong>Pattern analysis</strong><br>Which intents dominate?
</div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
<div style="padding:10px;background:var(--color-background-secondary);border-radius:8px;
font-size:11px;color:var(--color-text-secondary);line-height:1.6;text-align:center">
<div style="font-size:13px;margin-bottom:4px">🔄</div>
<strong>Model improvement</strong><br>Resolved convos → training data
</div>""", unsafe_allow_html=True)
    with col4:
        st.markdown("""
<div style="padding:10px;background:var(--color-background-secondary);border-radius:8px;
font-size:11px;color:var(--color-text-secondary);line-height:1.6;text-align:center">
<div style="font-size:13px;margin-bottom:4px">💼</div>
<strong>Business intelligence</strong><br>What gaps create confusion?
</div>""", unsafe_allow_html=True)

    with st.expander("Real LangSmith trace — what enterprise observability looks like"):
        st.code(f"""Trace ID: tr_8f92ka
├── input_guardrails      35ms    ✅
├── intent_classifier    {intent.get("processing_time_ms",142)}ms    ✅
├── rag_retrieval        {rag.get("processing_time_ms",89)}ms    ✅  score: {rag.get("best_score",0):.2f}
├── tool: lookup         {tools.get("calls",[{}])[0].get("latency",94) if tools.get("calls") else 94}ms    ✅
├── tool: check          {tools.get("calls",[{},{}])[1].get("latency",108) if len(tools.get("calls",[])) > 1 else 108}ms    ✅
├── llm_reasoning       {reasoning.get("processing_time_ms",1840)}ms    ✅  ~{reasoning.get("total_tokens",1600)} tokens
└── output_guardrails   {guardrails.get("processing_time_ms",270)}ms    {"🟡 modified" if guardrails.get("overall_status") == "modified" else "✅ pass"}
Total: {total_latency}ms | Est: ~${total_latency * 0.0000015:.4f} | Resolution: delivered""", language=None)
        st.caption("Source: LangSmith by LangChain — the industry standard for LLM observability. This is the real trace format.")

    render_enterprise_note(
        "Production observability uses Datadog, Honeycomb, or LangSmith with distributed tracing "
        "across every microservice. Anomaly detection runs automatically — statistical models "
        "flag unusual patterns in real time. LLM-as-judge evaluates 1% of conversations for "
        "quality, tone, and accuracy. Without observability, you're flying blind at scale."
    )

    render_risk_table(RISKS)

    # System architecture
    st.markdown("---")
    st.markdown("### 🏗️ System Architecture — You've been inside every box")
    st.markdown("Every layer we walked through maps to a block in this diagram.")

    st.image("https://via.placeholder.com/680x360/EBF4FD/378ADD?text=System+Architecture+Diagram", 
             caption="Architecture diagram — will be replaced with SVG in final build",
             use_container_width=True)

    # Actually render the architecture as code for now
    st.code("""
┌─────────────────────────────────────────────────────────────────┐
│  SECURITY LAYER                                                  │
│  [Authentication + Risk Score]  [Input Guardrails]             │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  CLASSIFICATION LAYER                                           │
│  [Intent Classifier — ML cascade → LLM for ambiguous cases]    │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  AGENTIC LAYER (iterates until confident)                       │
│  [RAG Retrieval] → [Tool Execution via MCP] → [LLM Reasoning]  │
│        ↑_____________________feedback loop______________________|
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  SAFETY LAYER                                                   │
│  [Output Guardrails: PII · Hallucination · Policy · Tone]      │
└─────────────────────────────┬───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  OBSERVABILITY LAYER                                            │
│  [Trace → Monitoring → Pattern Analysis → Model Improvement]   │
└─────────────────────────────────────────────────────────────────┘
""", language=None)

    st.success("🎉 You've seen the full pipeline — every layer, every decision, every output.")
    st.markdown(f"""
<div style="padding:14px;background:var(--color-background-secondary);border-radius:8px;
font-size:12px;color:var(--color-text-secondary);line-height:1.6;margin-top:8px">
💡 {content["why"]}
</div>
""", unsafe_allow_html=True)

    render_nav(back=True, next_label="Start over →")
