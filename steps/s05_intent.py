"""Step 5 — Intent classification: live API call with fallback."""
import streamlit as st
import time
import plotly.graph_objects as go
from config.content import STEP_INTROS, DOMAIN_TOOLS
from config.defaults import INTENT_LABELS
from ui import render_topbar, render_step_header, render_thinking_card, render_enterprise_note, render_risk_table, render_nav, render_what_we_built, render_error_card, render_fallback_badge
from state import get_llm_client, store_result, get_result, store_error, use_free_run, has_free_run

RISKS = [
    {
        "risk": "Misclassification",
        "example": '"My host is a nightmare" classified as complaint not escalation_request — wrong workflow triggered',
        "mitigation": "Confidence threshold — below 70% always routes to LLM classifier for second opinion",
    },
    {
        "risk": "Missing intents",
        "example": "New feature query falls into general_inquiry — generic response instead of specific help",
        "mitigation": "Monthly taxonomy review — flag all queries landing in general_inquiry and analyse clusters",
    },
    {
        "risk": "Sentiment over-indexing",
        "example": "Loudest user jumps priority queue over someone with a genuine urgent problem",
        "mitigation": "Weight urgency signals — time sensitivity, booking value, account history — not just tone",
    },
    {
        "risk": "Cascade failure",
        "example": "ML classifier down → all traffic hits LLM classifier → 10x cost spike overnight",
        "mitigation": "Circuit breaker — if ML classifier fails, route to rule-based fallback not LLM",
    },
]

FALLBACK_RESULT = {
    "primary_intent": "cancellation_request",
    "primary_confidence": 0.94,
    "secondary_intent": "refund_request",
    "secondary_confidence": 0.87,
    "sentiment": "neutral",
    "sentiment_confidence": 0.82,
    "urgency": "medium",
    "urgency_reason": "No immediate time pressure detected — trip not imminent",
    "all_scores": {
        "cancellation_request": 0.94, "refund_request": 0.87, "booking_inquiry": 0.12,
        "complaint": 0.08, "policy_question": 0.15, "escalation_request": 0.05,
        "general_inquiry": 0.03, "out_of_scope": 0.01,
    },
    "routing_suggestion": "standard_queue",
    "needs_tool_call": ["lookup_booking", "check_refund_eligibility"],
    "processing_time_ms": 142,
    "used_llm": True,
    "llm_reason": "Moderate confidence justified LLM for nuanced dual-intent detection",
}

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s05_intent"][domain]

    render_step_header("🎯", "Classification Layer — Intent Detection",
        "What does the AI think you're asking?")

    render_thinking_card(content["thinking"])

    # Run or retrieve result
    result = get_result("intent")
    used_fallback = False

    if not result:
        with st.spinner("Classifying your message..."):
            time.sleep(0.5)
            llm = get_llm_client()
            if llm:
                if has_free_run():
                    use_free_run()
                try:
                    from layers.intent_classifier import classify_intent
                    r = classify_intent(st.session_state.query, llm, domain)
                    result = r.__dict__
                    store_result("intent", result)
                except Exception as e:
                    store_error("intent", str(e))
                    result = FALLBACK_RESULT
                    used_fallback = True
            else:
                result = FALLBACK_RESULT
                used_fallback = True
            store_result("intent", result)

    if used_fallback:
        render_error_card("intent", "API call failed — showing pre-computed example")
        render_fallback_badge()

    # Results display
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:16px">
  <div style="font-size:11px;font-weight:500;color:var(--color-text-tertiary);letter-spacing:0.05em;margin-bottom:12px">CLASSIFICATION RESULT</div>
  <table style="width:100%;font-size:12px;border-collapse:collapse">
    <tr><td style="color:var(--color-text-tertiary);padding:5px 0">Primary intent</td>
        <td style="text-align:right"><code>{result.get("primary_intent","—")}</code>
        <span style="color:#378ADD"> {result.get("primary_confidence",0):.0%}</span></td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:5px 0">Secondary intent</td>
        <td style="text-align:right"><code>{result.get("secondary_intent") or "none"}</code>
        {"<span style='color:#BA7517'> " + f"{result.get('secondary_confidence',0):.0%}" + "</span>" if result.get("secondary_intent") else ""}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:5px 0">Sentiment</td>
        <td style="text-align:right;color:var(--color-text-primary)">{result.get("sentiment","—")} · {result.get("sentiment_confidence",0):.0%}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:5px 0">Urgency</td>
        <td style="text-align:right;color:var(--color-text-primary)">{result.get("urgency","—")}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:5px 0">Routing</td>
        <td style="text-align:right"><code>{result.get("routing_suggestion","—")}</code></td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:5px 0">Used LLM</td>
        <td style="text-align:right;color:var(--color-text-primary)">{"Yes" if result.get("used_llm") else "No — ML classifier sufficient"}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:5px 0">Processing time</td>
        <td style="text-align:right;color:var(--color-text-primary)">{result.get("processing_time_ms","—")}ms</td></tr>
  </table>
  <div style="margin-top:10px;font-size:11px;color:var(--color-text-tertiary);font-style:italic">
    {result.get("urgency_reason","")}
  </div>
</div>
""", unsafe_allow_html=True)

    # ML vs LLM cascade display
    st.markdown("**How the cascade ran:**")

    ml_color = "#1D9E75" if not result.get("used_llm") else "#BA7517"
    llm_color = "#1D9E75" if result.get("used_llm") else "#888780"
    ml_status = "✅ Ran — sufficient" if not result.get("used_llm") else "✅ Ran — low confidence, invoked LLM"
    llm_status = "✅ Invoked — low confidence query" if result.get("used_llm") else "⏭ Skipped — ML confidence was high enough"

    st.markdown(f"""
<div style="display:flex;gap:8px;margin-bottom:12px">
  <div style="flex:1;padding:10px 12px;background:var(--color-background-secondary);
  border:0.5px solid {ml_color};border-radius:8px">
    <div style="font-size:11px;font-weight:500;color:{ml_color};margin-bottom:4px">
      Stage 1 — ML Classifier · {result.get("ml_processing_time_ms","—")}ms
    </div>
    <div style="font-size:11px;color:var(--color-text-secondary)">{ml_status}</div>
    <div style="font-size:10px;color:var(--color-text-tertiary);margin-top:4px">
      Confidence: {result.get("ml_confidence",0):.0%}
    </div>
  </div>
  <div style="flex:1;padding:10px 12px;background:var(--color-background-secondary);
  border:0.5px solid {llm_color};border-radius:8px">
    <div style="font-size:11px;font-weight:500;color:{llm_color};margin-bottom:4px">
      Stage 2 — LLM Classifier · {result.get("llm_processing_time_ms",0) or "—"}ms
    </div>
    <div style="font-size:11px;color:var(--color-text-secondary)">{llm_status}</div>
    <div style="font-size:10px;color:var(--color-text-tertiary);margin-top:4px">
      {result.get("llm_reason","") if result.get("used_llm") else "Not needed"}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    with col2:
        # Confidence chart
        scores = result.get("all_scores", {})
        if scores:
            sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
            primary = result.get("primary_intent")
            secondary = result.get("secondary_intent")
            colors = ["#378ADD" if k == primary else "#BA7517" if k == secondary else "#D3D1C7" for k in sorted_scores.keys()]
            fig = go.Figure(go.Bar(
                x=list(sorted_scores.values()),
                y=[k.replace("_", " ") for k in sorted_scores.keys()],
                orientation='h',
                marker_color=colors,
            ))
            fig.update_layout(
                height=240, margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(range=[0, 1], title="Confidence"),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("🔵 Primary · 🟡 Secondary · Gray = considered but below threshold")

    # Intent taxonomy
    with st.expander("Our full intent taxonomy — all 8 intents"):
        st.markdown("""
| Intent | Example query |
|---|---|
| `cancellation_request` | "I want to cancel my booking" |
| `refund_request` | "Can I get my money back?" |
| `booking_inquiry` | "When is my check-in time?" |
| `complaint` | "The apartment was completely filthy" |
| `policy_question` | "What is the strict cancellation policy?" |
| `escalation_request` | "I need to speak to a human agent" |
| `general_inquiry` | "How does this platform work?" |
| `out_of_scope` | "What's the weather in Barcelona?" |
""")

    render_what_we_built(
    "We use a two-stage cascade. A scikit-learn TF-IDF + Logistic Regression classifier "
    "runs first on every message, trained on 120 labeled examples across 8 intents, runs "
    "in under 5ms. If confidence is above 75%, the result is used directly and Gemini is "
    "never called. Only ambiguous or low-confidence messages invoke the LLM — saving API "
    "cost and reducing latency for the majority of queries."
    )

    render_enterprise_note(
        "Airbnb maintains 50-100 intent categories updated quarterly. New patterns emerge from "
        "production data — when enough users ask something similar that doesn't fit existing "
        "categories, the taxonomy gets expanded. That's a product decision, not an engineering one. "
        "The cascade architecture saves 60-70% on LLM costs at scale."
    )

    render_risk_table(RISKS)

    render_nav(back=True, next_label="Next: The Agentic Layer →")
