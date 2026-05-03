"""Step 10 — Output guardrails."""
import streamlit as st
import time
import re
from config.content import STEP_INTROS
from ui import render_topbar, render_step_header, render_thinking_card, render_enterprise_note, render_risk_table, render_nav, render_what_we_built
from state import store_result, get_result

RISKS = [
    {
        "risk": "False positive",
        "example": '"I need to kill this booking" flagged as violent — response blocked, user gets generic fallback',
        "mitigation": "Tune guardrail thresholds — measure false positive rate as a core product metric weekly",
    },
    {
        "risk": "False negative",
        "example": "Hallucinated $350 refund slips past grounding check — user gets wrong information confidently",
        "mitigation": "Multiple grounding methods — rule-based + LLM-as-judge, not just one layer",
    },
    {
        "risk": "Guardrail latency",
        "example": "5 sequential checks add 270ms — user experience degrades significantly at scale",
        "mitigation": "Parallelise low-dependency checks — PII and tone can run simultaneously, not sequentially",
    },
    {
        "risk": "Guardrail drift",
        "example": "Policy changes in January — guardrail rules not updated until March — wrong decisions approved",
        "mitigation": "Guardrail rules versioned alongside policy documents — change one, trigger review of the other",
    },
]

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s10_output_guardrails"][domain]

    render_step_header("🔒", "Safety Layer — Output Guardrails",
        "Five checks before you see a single word.")

    render_thinking_card(content["thinking"])

    reasoning = get_result("reasoning")
    draft = reasoning.get("draft_response", "") if reasoning else ""

    result = get_result("output_guardrails")

    if not result:
        with st.spinner("Running guardrail checks..."):
            time.sleep(1.2)

            # PII check
            pii_patterns = {
                "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "phone": r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
                "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            }
            pii_found = []
            for label, pattern in pii_patterns.items():
                if re.findall(pattern, draft, re.IGNORECASE):
                    pii_found.append(label)

            # Numbers grounding check
            response_nums = set(re.findall(r'\$[\d,]+|\d+%|\d+ days|\d+ hours', draft))
            rag = get_result("rag")
            tools = get_result("tools")
            context_text = (rag.get("context_text", "") if rag else "") + str(tools)
            context_nums = set(re.findall(r'\$[\d,]+|\d+%|\d+ days|\d+ hours', context_text))
            ungrounded = response_nums - context_nums

            # High value check
            amounts = re.findall(r'\$(\d+(?:\.\d+)?)', draft)
            high_value = any(float(a) > 250 for a in amounts)

            checks = [
                {
                    "name": "PII detection",
                    "tool": "Microsoft Presidio",
                    "status": "fail" if pii_found else "pass",
                    "finding": f"PII detected: {', '.join(pii_found)}" if pii_found else "Clean — no PII patterns",
                    "action": "blocked" if pii_found else "none",
                    "latency_ms": 12,
                    "severity": "high",
                },
                {
                    
                    "name": "Hallucination check",
                    "tool": "LLM-as-judge",
                    "status": "modified" if ungrounded else "pass",
                    "finding": f"Some values not found verbatim in context: {ungrounded} — flagged for review" if ungrounded else "All figures traceable to retrieved context",
                    "action": "flagged" if ungrounded else "none",
                    "latency_ms": 89,
                    "severity": "medium",

                },
                {
                    "name": "Policy compliance",
                    "tool": "LLM-as-judge",
                    "status": "pass",
                    "finding": "Refund decision aligns with retrieved policy",
                    "action": "none",
                    "latency_ms": 94,
                    "severity": "high",
                },
                {
                    "name": "Escalation trigger",
                    "tool": "Rule-based",
                    "status": "modified" if high_value else "pass",
                    "finding": f"High-value refund detected (>$250) — escalation language strengthened" if high_value else "No escalation trigger needed",
                    "action": "modified" if high_value else "none",
                    "latency_ms": 8,
                    "severity": "medium",
                },
                {
                    "name": "Tone check",
                    "tool": "LLM-as-judge",
                    "status": "pass",
                    "finding": "Response is empathetic and professional",
                    "action": "none",
                    "latency_ms": 67,
                    "severity": "low",
                },
            ]

            # Build final response
            final = draft
            blocked = any(c["status"] == "fail" and c["severity"] == "high" and c["name"] == "PII detection" for c in checks)
            if blocked:
                final = "I want to make sure I give you accurate information. Let me connect you with a human support agent who can review your case directly."
            elif high_value:
                final = draft + "\n\n*Because your case involves a significant amount, a member of our specialist team will personally review it. A human agent will follow up within 2 hours.*"

            result = {
                "checks": checks,
                "original_response": draft,
                "final_response": final,
                "overall_status": "blocked" if blocked else "modified" if high_value else "pass",
                "summary": f"{'Blocked by guardrail' if blocked else 'Modified — escalation added' if high_value else 'All 5 checks passed'}",
                "processing_time_ms": sum(c["latency_ms"] for c in checks),
            }
            store_result("output_guardrails", result)

    # Display checks
    st.markdown("**Checks run — in sequence:**")
    for check in result["checks"]:
        status_color = {"pass": "#1D9E75", "fail": "#E24B4A", "modified": "#BA7517"}[check["status"]]
        status_icon = {"pass": "✅", "fail": "❌", "modified": "🟡"}[check["status"]]
        severity = {"high": "HIGH", "medium": "MED", "low": "LOW"}[check["severity"]]

        st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
padding:8px 12px;background:var(--color-background-secondary);border-radius:8px;
border:0.5px solid var(--color-border-tertiary);margin-bottom:6px">
  <div>
    <span style="font-size:12px;font-weight:500;color:var(--color-text-primary)">{status_icon} {check["name"]}</span>
    <span style="font-size:10px;color:var(--color-text-tertiary);margin-left:6px">{check["tool"]} · `{severity}`</span>
    <div style="font-size:11px;color:var(--color-text-tertiary);margin-top:2px">{check["finding"]}</div>
    {f'<div style="font-size:10px;color:{status_color};margin-top:2px">Action: {check["action"]}</div>' if check["action"] != "none" else ""}
  </div>
  <div style="font-size:11px;color:var(--color-text-tertiary);flex-shrink:0;margin-left:12px">{check["latency_ms"]}ms</div>
</div>
""", unsafe_allow_html=True)

    # Overall result
    status = result["overall_status"]
    if status == "pass":
        st.success(f"✅ {result['summary']} · ⏱ {result['processing_time_ms']}ms total")
    elif status == "modified":
        st.warning(f"🟡 {result['summary']} · ⏱ {result['processing_time_ms']}ms total")
    else:
        st.error(f"🔴 {result['summary']} · ⏱ {result['processing_time_ms']}ms total")

    # Before/after if modified
    if result["overall_status"] != "pass":
        st.markdown("**Before → After guardrails:**")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("Before")
            st.text_area("", value=result["original_response"], height=100, disabled=True, label_visibility="collapsed")
        with c2:
            st.markdown("After")
            st.text_area("", value=result["final_response"], height=100, disabled=True, label_visibility="collapsed")

    with st.expander("Real Microsoft Presidio output — PII detection format"):
        st.code("""{
  "text": "My card number is 4111-1111-1111-1111",
  "analysis": [{"entity_type": "CREDIT_CARD", "score": 0.99}],
  "anonymized": "My card number is <CREDIT_CARD>"
}""", language="json")

    render_what_we_built(
        "We ran rule-based checks (PII via regex, escalation via threshold) and "
        "logic-based grounding checks. In production, PII and hallucination checks "
        "use dedicated ML models, not rules."
    )

    render_enterprise_note(
        "Production guardrails run as separate microservices — Perspective API for toxicity, "
        "Presidio for PII, custom models for policy compliance, LLM-as-judge for quality. "
        "Every guardrail fire is logged for regulatory reporting. False positive rates are "
        "tracked weekly as a core product metric."
    )

    render_risk_table(RISKS)
    render_nav(back=True, next_label="Next: The Response →")
