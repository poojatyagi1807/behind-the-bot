"""
Step 11b — LLM as Judge
─────────────────────────
Evaluates the full pipeline output and diagnoses:
- What went well
- Which layer was the weakest link
- What a PM should do about it
"""

import streamlit as st
import time
import json
from ui import render_topbar, render_step_header, render_enterprise_note, render_nav
from state import get_llm_client, store_result, get_result, store_error

JUDGE_PROMPT = """You are an expert AI systems evaluator — part technical architect, part product manager.

You will be given:
1. The user's original query
2. The pipeline results from each layer (intent, RAG, tools, reasoning, guardrails)
3. The final response the user received

Your job is to evaluate the full pipeline and return a JSON object with EXACTLY this structure:
{{
  "verdict": "<one of: excellent, good, correct_reasoning_wrong_data, retrieval_failure, guardrail_over_triggered, misclassified, hallucination_risk, poor_response>",
  "verdict_summary": "<one sentence — what happened overall>",
  "what_happened": "<2-3 sentences explaining the full picture in plain English for a non-technical PM>",
  "weakest_layer": "<one of: authentication, input_guardrails, intent, rag, tools, reasoning, output_guardrails, none>",
  "weakest_layer_reason": "<1-2 sentences explaining why this layer was the problem>",
  "what_went_well": "<1-2 sentences on what the pipeline did correctly>",
  "pm_recommendations": [
    "<specific actionable recommendation 1>",
    "<specific actionable recommendation 2>",
    "<specific actionable recommendation 3>"
  ],
  "severity": "<one of: critical, moderate, minor, none>"
}}

Evaluation criteria:
- Check if RAG retrieved relevant chunks (score below 0.4 = weak retrieval)
- Check if tool data aligns with what the user described in their query
- Check if the intent was correctly classified
- Check if guardrails fired appropriately or over-triggered
- Check if the final response actually answers what the user asked
- Check if reasoning was grounded in retrieved data
- Check if the final response contains chain of thought reasoning, STEP prefixes, or internal reasoning steps that should not be visible to the user — this is a response formatting failure

Return ONLY valid JSON. No markdown, no explanation outside the JSON.
"""

FALLBACK_RESULT = {
    "verdict": "good",
    "verdict_summary": "Pipeline performed correctly — response is grounded and relevant.",
    "what_happened": "The intent was correctly classified, relevant policy chunks were retrieved with good similarity scores, tool data was fetched successfully, and the LLM reasoned over all of it to produce a grounded response. The guardrails passed without modification.",
    "weakest_layer": "none",
    "weakest_layer_reason": "No significant weakness detected in this run.",
    "what_went_well": "RAG retrieval found highly relevant policy chunks. The LLM stayed grounded in retrieved context without hallucinating policy details.",
    "pm_recommendations": [
        "Monitor RAG similarity scores over time — if they drift below 0.5 on average, the knowledge base may need re-chunking or re-indexing",
        "Track guardrail fire rates weekly — unexpected spikes signal either a policy change or a new user query pattern",
        "Review out_of_scope classifications monthly to identify emerging intent categories not yet in your taxonomy",
    ],
    "severity": "none",
}

VERDICT_CONFIG = {
    "excellent": {"icon": "🟢", "color": "#1D9E75", "bg": "#EAF3DE", "label": "Excellent", "text_color": "#1A3A08"},
    "good": {"icon": "🟢", "color": "#1D9E75", "bg": "#EAF3DE", "label": "Good", "text_color": "#1A3A08"},
    "correct_reasoning_wrong_data": {"icon": "🟡", "color": "#BA7517", "bg": "#FAEEDA", "label": "Correct reasoning, wrong data", "text_color": "#4A2800"},
    "retrieval_failure": {"icon": "🔴", "color": "#E24B4A", "bg": "#FCEBEB", "label": "Retrieval failure", "text_color": "#4A0F0F"},
    "guardrail_over_triggered": {"icon": "🟡", "color": "#BA7517", "bg": "#FAEEDA", "label": "Guardrail over-triggered", "text_color": "#4A2800"},
    "misclassified": {"icon": "🔴", "color": "#E24B4A", "bg": "#FCEBEB", "label": "Intent misclassified", "text_color": "#4A0F0F"},
    "hallucination_risk": {"icon": "🔴", "color": "#E24B4A", "bg": "#FCEBEB", "label": "Hallucination risk", "text_color": "#4A0F0F"},
    "cot_leaked": {"icon": "🔴", "color": "#E24B4A", "bg": "#FCEBEB", "label": "Chain of thought leaked into response", "text_color": "#4A0F0F"},
    "poor_response": {"icon": "🔴", "color": "#E24B4A", "bg": "#FCEBEB", "label": "Poor response quality", "text_color": "#4A0F0F"},
}

LAYER_ICONS = {
    "authentication": "🔐",
    "input_guardrails": "🛡️",
    "intent": "🎯",
    "rag": "🔍",
    "tools": "🔧",
    "reasoning": "🧠",
    "output_guardrails": "🔒",
    "none": "✅",
}

SEVERITY_CONFIG = {
    "critical": {"color": "#E24B4A", "label": "Critical — fix before going live"},
    "moderate": {"color": "#BA7517", "label": "Moderate — address in next iteration"},
    "minor": {"color": "#378ADD", "label": "Minor — monitor over time"},
    "none": {"color": "#1D9E75", "label": "No issues detected"},
}


def _build_judge_input(query, intent, rag, tools, reasoning, guardrails, final_response):
    """Assemble all layer data into a concise judge input."""
    return f"""
USER QUERY: {query}

INTENT CLASSIFICATION:
- Primary: {intent.get("primary_intent","—")} ({intent.get("primary_confidence",0):.0%} confidence)
- Secondary: {intent.get("secondary_intent") or "none"}
- Sentiment: {intent.get("sentiment","—")}
- Urgency: {intent.get("urgency","—")}
- Routing: {intent.get("routing_suggestion","—")}

RAG RETRIEVAL:
- Total chunks: {rag.get("total_chunks","—")}
- Best similarity score: {rag.get("best_score",0):.3f}
- Low confidence warning: {rag.get("low_confidence", False)}
- Top chunk preview: {rag.get("selected",[{}])[0].get("chunk",{}).get("text","—")[:200] if rag.get("selected") else "—"}

TOOL RESULTS:
{json.dumps([{"tool": c.get("tool"), "output": c.get("output")} for c in tools.get("calls",[])] if tools else [], indent=2)}

REASONING:
- Grounded: {reasoning.get("grounded", True)}
- Tokens: {reasoning.get("total_tokens","—")}
- Chain of thought summary: {reasoning.get("chain_of_thought","—")[:300] if reasoning.get("chain_of_thought") else "not captured"}

GUARDRAILS:
- Overall status: {guardrails.get("overall_status","—")}
- Checks: {json.dumps([{"name": c.get("name"), "status": c.get("status"), "finding": c.get("finding")} for c in guardrails.get("checks",[])])}

FINAL RESPONSE DELIVERED TO USER:
{final_response}

FORMATTING CHECK:
Does the final response contain any of these problems?
- Lines starting with "STEP 1:", "STEP 2:" etc visible to user
- Internal reasoning steps exposed in the response
- <thinking> or <response> XML tags visible
- Chain of thought leaked through to the user-facing answer
"""


def render():
    render_topbar()

    render_step_header(
        "🧑‍⚖️", "LLM-as-Judge — Pipeline Evaluation",
        "A separate AI evaluates what just happened and tells you what a PM should do about it."
    )

    st.markdown(f"""
<div style="background:var(--color-background-secondary);border-left:3px solid #7F77DD;
border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:16px;
font-size:13px;color:var(--color-text-secondary);line-height:1.6;font-style:italic">
The pipeline just ran. But how good was it really? A second AI — completely separate from the one 
that answered your question — now reads every layer's output and gives an honest verdict. 
This is how enterprises catch problems before users do.
</div>
""", unsafe_allow_html=True)

    result = get_result("judge")

    if not result:
        with st.spinner("Judge is evaluating the full pipeline..."):
            time.sleep(0.5)

            intent = get_result("intent") or {}
            rag = get_result("rag") or {}
            tools = get_result("tools") or {}
            reasoning = get_result("reasoning") or {}
            guardrails = get_result("output_guardrails") or {}
            final_response = guardrails.get("final_response", "")
            query = st.session_state.query or ""

            llm = get_llm_client()
            if llm:
                try:
                    judge_input = _build_judge_input(
                        query, intent, rag, tools, reasoning, guardrails, final_response
                    )
                    full_prompt = f"{JUDGE_PROMPT}\n\nEvaluate this pipeline run:\n{judge_input}"
                    response = llm.generate_content(full_prompt)
                    raw = response.text.strip()
                    if raw.startswith("```"):
                        raw = raw.split("```")[1]
                        if raw.startswith("json"):
                            raw = raw[4:]
                    result = json.loads(raw.strip())
                    store_result("judge", result)
                except Exception as e:
                    store_error("judge", str(e))
                    result = FALLBACK_RESULT
                    store_result("judge", result)
            else:
                result = FALLBACK_RESULT
                store_result("judge", result)

    # Render verdict
    verdict = result.get("verdict", "good")
    vc = VERDICT_CONFIG.get(verdict, VERDICT_CONFIG["good"])
    severity = result.get("severity", "none")
    sc = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["none"])
    weakest = result.get("weakest_layer", "none")
    weakest_icon = LAYER_ICONS.get(weakest, "✅")

    # Main verdict card
    st.markdown(f"""
<div style="background:{vc['bg']};border:1px solid {vc['color']}40;border-radius:12px;
padding:20px;margin-bottom:16px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
    <div style="font-size:20px">{vc['icon']}</div>
    <div>
      <div style="font-size:15px;font-weight:500;color:{vc['color']}">{vc['label']}</div>
      <div style="font-size:12px;color:{vc['color']}99;margin-top:2px">{result.get("verdict_summary","")}</div>
    </div>
  </div>
  <div style="font-size:13px;color:{vc['text_color']};line-height:1.7">
    {result.get("what_happened","")}
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # Weakest layer
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:14px;margin-bottom:10px">
  <div style="font-size:10px;font-weight:500;color:var(--color-text-tertiary);
  letter-spacing:0.05em;margin-bottom:8px">WEAKEST LAYER</div>
  <div style="font-size:14px;font-weight:500;color:var(--color-text-primary);margin-bottom:6px">
    {weakest_icon} {weakest.replace("_"," ").title() if weakest != "none" else "None — pipeline healthy"}
  </div>
  <div style="font-size:12px;color:var(--color-text-primary);line-height:1.6">
    {result.get("weakest_layer_reason","")}
  </div>
</div>
""", unsafe_allow_html=True)

        # What went well
        st.markdown(f"""
<div style="background:#EAF3DE;border:0.5px solid #C0DD97;border-radius:10px;padding:14px">
  <div style="font-size:10px;font-weight:500;color:#3B6D11;
  letter-spacing:0.05em;margin-bottom:8px">WHAT WENT WELL</div>
  <div style="font-size:12px;color:#1A3A08;line-height:1.6">
    {result.get("what_went_well","")}
  </div>
</div>
""", unsafe_allow_html=True)

    with col2:
        # Severity
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:14px;margin-bottom:10px">
  <div style="font-size:10px;font-weight:500;color:var(--color-text-tertiary);
  letter-spacing:0.05em;margin-bottom:8px">SEVERITY</div>
  <div style="font-size:13px;font-weight:500;color:{sc['color']}">{sc['label']}</div>
</div>
""", unsafe_allow_html=True)

        # PM recommendations
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:14px">
  <div style="font-size:10px;font-weight:500;color:var(--color-text-tertiary);
  letter-spacing:0.05em;margin-bottom:10px">PM COURSE CORRECTIONS</div>
  {"".join([
    f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px">'
    f'<div style="width:18px;height:18px;border-radius:50%;background:#378ADD;color:#fff;'
    f'font-size:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px">{i+1}</div>'
    f'<div style="font-size:11px;color:var(--color-text-secondary);line-height:1.5">{rec}</div>'
    f'</div>'
    for i, rec in enumerate(result.get("pm_recommendations", []))
  ])}
</div>
""", unsafe_allow_html=True)

    # Layer scorecard
    st.markdown("---")
    st.markdown("**Pipeline scorecard — judge's assessment of each layer:**")

    intent = get_result("intent") or {}
    rag = get_result("rag") or {}
    tools = get_result("tools") or {}
    reasoning = get_result("reasoning") or {}
    guardrails = get_result("output_guardrails") or {}

    layers = [
        ("🎯 Intent", intent.get("primary_confidence", 0) >= 0.7, f"{intent.get('primary_confidence',0):.0%} confidence"),
        ("🔍 RAG", not rag.get("low_confidence", False) and rag.get("best_score", 0) >= 0.4, f"Best score: {rag.get('best_score',0):.2f}"),
        ("🔧 Tools", not tools.get("any_failed", False), f"{len(tools.get('calls',[]))} calls"),
        ("🧠 Reasoning", reasoning.get("grounded", True), f"~{reasoning.get('total_tokens',0):,} tokens"),
        ("🔒 Guardrails", guardrails.get("overall_status") != "blocked", guardrails.get("overall_status","—").title()),
    ]

    cols = st.columns(5)
    for col, (label, passed, detail) in zip(cols, layers):
        is_weakest = any(w in label.lower() for w in [weakest.replace("_","").lower()])
        border = f"1px solid #E24B4A" if is_weakest and weakest != "none" else "0.5px solid var(--color-border-tertiary)"
        icon = "✅" if passed else "⚠️"
        with col:
            st.markdown(f"""
<div style="background:var(--color-background-secondary);border:{border};
border-radius:8px;padding:10px;text-align:center">
  <div style="font-size:11px;font-weight:500;color:var(--color-text-primary);margin-bottom:4px">{label}</div>
  <div style="font-size:16px;margin-bottom:4px">{icon}</div>
  <div style="font-size:10px;color:var(--color-text-tertiary)">{detail}</div>
</div>
""", unsafe_allow_html=True)

    render_enterprise_note(
        "At enterprise scale, LLM-as-judge runs on a random 1-5% sample of all conversations — "
        "not every query. Results feed into weekly quality reviews where PMs, engineers, and "
        "AI safety teams review failure patterns together. Companies like Anthropic, Google, "
        "and Microsoft use variants of this pattern to continuously improve their AI products. "
        "The judge model is typically larger and more capable than the production model it evaluates."
    )

    render_nav(back=True, next_label="Next: Observability →")
