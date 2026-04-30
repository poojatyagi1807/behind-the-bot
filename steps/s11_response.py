"""Step 11 — The final response."""
import streamlit as st
from config.content import STEP_INTROS
from ui import render_topbar, render_step_header, render_nav
from state import get_result

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s11_response"][domain]
    profile = st.session_state.profile

    render_step_header("💬", "The Response",
        "Nine layers of processing. One clean answer.")

    guardrail_result = get_result("output_guardrails")
    final_response = guardrail_result.get("final_response", "") if guardrail_result else ""
    status = guardrail_result.get("overall_status", "pass") if guardrail_result else "pass"

    if status == "blocked":
        st.error("Response was blocked by guardrails — safe fallback served.")
    elif status == "modified":
        st.warning("Response was modified by a guardrail before delivery.")

    # Chat bubble
    name = profile["name"] if profile else "You"
    st.markdown(f"""
<div style="margin:16px 0">
  <div style="display:flex;justify-content:flex-end;margin-bottom:8px">
    <div style="background:#378ADD;color:#fff;border-radius:16px 16px 4px 16px;
    padding:10px 14px;max-width:75%;font-size:13px;line-height:1.6">
      {st.session_state.query}
    </div>
  </div>
  <div style="display:flex;justify-content:flex-start">
    <div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
    border-radius:16px 16px 16px 4px;padding:12px 16px;max-width:85%;font-size:13px;line-height:1.7;
    color:var(--color-text-primary)">
      {final_response.replace(chr(10), '<br>')}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    # The invisible work
    st.markdown("**What happened invisibly before that response appeared:**")

    intent = get_result("intent")
    rag = get_result("rag")
    tools = get_result("tools")
    reasoning = get_result("reasoning")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        conf = intent.get("primary_confidence", 0) if intent else 0
        st.metric("🎯 Intent", f"{conf:.0%}", delta=intent.get("primary_intent","—").replace("_"," ") if intent else "—")
    with col2:
        score = rag.get("best_score", 0) if rag else 0
        st.metric("🔍 RAG", f"{score:.2f}", delta=f"{rag.get('total_chunks',0)} chunks" if rag else "—")
    with col3:
        calls = len(tools.get("calls", [])) if tools else 0
        st.metric("🔧 Tools", f"{calls} calls", delta="All succeeded")
    with col4:
        ms = reasoning.get("processing_time_ms", 0) if reasoning else 0
        st.metric("🧠 Reasoning", f"{ms}ms", delta=f"~{reasoning.get('total_tokens',0):,} tokens" if reasoning else "—")
    with col5:
        status_label = {"pass": "✓ Pass", "modified": "~ Modified", "blocked": "✗ Blocked"}.get(status, "—")
        st.metric("🛡️ Guardrails", status_label, delta="5 checks")

    st.markdown(f"""
<div style="margin-top:16px;padding:12px 14px;background:var(--color-background-secondary);
border-radius:8px;font-size:12px;color:var(--color-text-secondary);line-height:1.6;
font-style:italic">{content["thinking"]}</div>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div style="margin-top:8px;padding:10px 14px;background:#EAF3DE;border-radius:8px;
font-size:12px;color:#3B6D11;line-height:1.6">
💡 <strong>Why this matters:</strong> {content["why"]}
</div>
""", unsafe_allow_html=True)

    render_nav(back=True, next_label="Next: Observability →")
