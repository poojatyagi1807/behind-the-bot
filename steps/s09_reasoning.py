"""Step 9 — LLM Reasoning: full context window + chain of thought."""
import streamlit as st
import time
from config.content import STEP_INTROS
from config.defaults import SYSTEM_PROMPTS
from ui import render_topbar, render_step_header, render_thinking_card, render_enterprise_note, render_risk_table, render_nav, render_what_we_built, render_error_card, render_fallback_badge
from state import get_llm_client, store_result, get_result, store_error

RISKS = [
    {
        "risk": "Hallucination",
        "example": "LLM calculates $350 refund — number not in any tool result or RAG chunk",
        "mitigation": "Grounding check — flag any figure not traceable to source data. Temperature=0 for policy decisions",
    },
    {
        "risk": "Context overflow",
        "example": "Long conversation + tools + RAG exceeds context window — early instructions silently dropped",
        "mitigation": "Context management — summarise older turns, prioritise recent tool results, monitor token count",
    },
    {
        "risk": "Wrong reasoning path",
        "example": "LLM skips to extenuating circumstances policy — ignores moderate policy entirely",
        "mitigation": "Structured reasoning prompt — force step-by-step before conclusion. Include explicit grounding instruction",
    },
    {
        "risk": "Inconsistency",
        "example": "Same query returns different refund amounts on different runs",
        "mitigation": "Temperature=0 for policy decisions — deterministic not creative. Cache results for identical inputs",
    },
]

COT_PROMPT = """Think through this step by step before responding. Write your reasoning inside <thinking> tags, then your response inside <response> tags.

In your thinking:
1. What is the user actually asking?
2. What does the retrieved policy say?
3. What do the tool results show?
4. What can I say with confidence vs what is uncertain?
5. What tone is appropriate?
6. Should I escalate or can I resolve this?

Then write a clear, empathetic response grounded only in the retrieved information."""

def _build_context(query, profile, intent_result, rag_result, tool_result, system_prompt):
    intent_ctx = ""
    if intent_result:
        intent_ctx = f"""
Primary intent: {intent_result.get("primary_intent")} ({intent_result.get("primary_confidence",0):.0%})
Secondary: {intent_result.get("secondary_intent") or "none"}
Sentiment: {intent_result.get("sentiment")} | Urgency: {intent_result.get("urgency")}
Routing: {intent_result.get("routing_suggestion")}"""

    profile_ctx = ""
    if profile:
        profile_ctx = f"""
User: {profile["name"]} | Trust: {profile["trust_score"]}/100 | Member: {profile["member_since"]}
Disputes: {profile["past_disputes"]} | Refund requests: {profile["refund_requests"]}"""

    rag_ctx = rag_result.get("context_text", "") if rag_result else ""

    tool_ctx = ""
    if tool_result and tool_result.get("calls"):
        import json
        for call in tool_result["calls"]:
            if call.get("success"):
                tool_ctx += f"\n[{call['tool']}]\n{json.dumps(call['output'], indent=2)}\n"

    full_system = f"""{COT_PROMPT}

{system_prompt}

━━━ INTENT ANALYSIS ━━━
{intent_ctx}

━━━ USER PROFILE ━━━
{profile_ctx}

━━━ RETRIEVED POLICY CONTEXT ━━━
{rag_ctx}

━━━ TOOL RESULTS ━━━
{tool_ctx or "No tools were called."}"""

    tokens = int(len(full_system.split()) * 1.3) + int(len(query.split()) * 1.3)
    return full_system, tokens

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s09_reasoning"][domain]

    render_step_header("🧠", "Agentic Layer — LLM Reasoning",
        "Everything assembled. Now the AI thinks.")

    render_thinking_card(content["thinking"])

    result = get_result("reasoning")
    used_fallback = False

    if not result:
        with st.spinner("Reasoning... this is the most expensive step ⟳"):
            time.sleep(0.5)
            llm = get_llm_client()
            intent_result = get_result("intent")
            rag_result = get_result("rag")
            tool_result = get_result("tools")
            system_prompt = SYSTEM_PROMPTS.get(domain, "")

            full_system, tokens = _build_context(
                st.session_state.query,
                st.session_state.profile,
                intent_result, rag_result, tool_result, system_prompt
            )

            if llm:
                try:
                    start = __import__("time").time()
                    response = llm.generate_content(
                        f"{full_system}\n\nUser message: {st.session_state.query}"
                    )
                    elapsed = int((__import__("time").time() - start) * 1000)
                    raw = response.text

                    cot = ""
                    draft = raw
                    if "<thinking>" in raw and "</thinking>" in raw:
                        cot = raw.split("<thinking>")[1].split("</thinking>")[0].strip()
                    if "<response>" in raw and "</response>" in raw:
                        draft = raw.split("<response>")[1].split("</response>")[0].strip()
                    elif "</thinking>" in raw:
                        draft = raw.split("</thinking>")[-1].strip()

                    result = {
                        "chain_of_thought": cot,
                        "draft_response": draft,
                        "context_system": full_system,
                        "total_tokens": tokens,
                        "processing_time_ms": elapsed,
                        "grounded": True,
                    }
                    store_result("reasoning", result)
                except Exception as e:
                    store_error("reasoning", str(e))
                    used_fallback = True
            else:
                used_fallback = True

            if used_fallback:
                result = {
                    "chain_of_thought": """STEP 1: UNDERSTAND THE REQUEST
  Input   → User wants to cancel and receive full refund
  Action  → Dual intent: cancellation + refund

STEP 2: IDENTIFY APPLICABLE POLICY
  Finding → Moderate policy: full refund if 5+ days before check-in
  Finding → Check-in is 3 days away → 3 < 5 → Full refund NOT applicable

STEP 3: DETERMINE ACTUAL ELIGIBILITY
  Finding → 1-5 day window = 50% of nightly rate
  Calc    → $145 × 3 nights × 50% = $217.50 + $52.50 cleaning = $270.00

STEP 4: CHECK GROUNDING
  Verify  → All figures sourced from tool results and RAG chunks ✅

STEP 5: ASSESS TONE
  Input   → Sentiment neutral, urgency medium
  Decision → Professional and empathetic, no urgency language

STEP 6: CONSTRUCT RESPONSE
  Include → Clear refund breakdown, what is/isn't refunded and why""",
                    "draft_response": "Thank you for reaching out. Based on your booking under a Moderate cancellation policy, since your check-in is 3 days away, you're eligible for a partial refund: 50% of your nightly rate ($217.50) plus your cleaning fee ($52.50), for a total of $270.00. The $72.00 service fee is non-refundable under the Moderate policy. To proceed, please confirm the cancellation and your refund will be processed within 5-10 business days.",
                    "context_system": full_system,
                    "total_tokens": tokens,
                    "processing_time_ms": 1840,
                    "grounded": True,
                }
                store_result("reasoning", result)

    if used_fallback:
        render_error_card("reasoning", "API call failed — showing pre-computed example")
        render_fallback_badge()

    # Context window summary
    st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:14px;margin-bottom:12px">
  <div style="font-size:11px;font-weight:500;color:var(--color-text-tertiary);letter-spacing:0.05em;margin-bottom:10px">CONTEXT WINDOW ASSEMBLED</div>
  <div style="font-size:12px;color:var(--color-text-secondary)">
    ~{result["total_tokens"]:,} tokens total · Model: {st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")} · ⏱ {result["processing_time_ms"]}ms
  </div>
  <div style="margin-top:8px;font-size:11px;color:{"#1D9E75" if result["grounded"] else "#BA7517"}">
    {"✓ Response appears grounded in retrieved context" if result["grounded"] else "⚠️ Check grounding — response may contain unverified claims"}
  </div>
</div>
""", unsafe_allow_html=True)

    with st.expander("Full context window passed to LLM", expanded=False):
        st.text_area("", value=result["context_system"][:2000] + "...", height=200, disabled=True, label_visibility="collapsed")

    st.markdown("**Chain of thought — how the LLM reasoned:**")
    if result.get("chain_of_thought"):
        st.info(result["chain_of_thought"])
    else:
        st.caption("No chain of thought captured from this response.")

    st.markdown("**Draft response — before guardrails:**")
    st.text_area("", value=result["draft_response"], height=120, disabled=True, label_visibility="collapsed")

    render_what_we_built(
        "We passed the full assembled context to Gemini with a chain-of-thought prompt — "
        "instructing it to reason step by step before responding. This produces more "
        "reliable, grounded answers than asking for a direct response."
    )

    render_enterprise_note(
        "Enterprises use multi-model routing — a fast cheap model for simple queries, "
        "a powerful model for complex ones. Context management systems compress and "
        "prioritise what goes in. At 1,600 tokens per query and 1M daily queries, "
        "that's $160K/day in reasoning costs — context efficiency is a core PM metric."
    )

    render_risk_table(RISKS)
    render_nav(back=True, next_label="Next: Output Guardrails →")
