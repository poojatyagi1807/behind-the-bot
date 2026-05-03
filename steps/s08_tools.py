"""Step 8 — Tool execution: simulated domain-specific tools."""
import streamlit as st
import time
import random
from datetime import datetime, timedelta
from config.content import STEP_INTROS
from ui import render_topbar, render_step_header, render_thinking_card, render_enterprise_note, render_risk_table, render_nav, render_what_we_built
from state import store_result, get_result

RISKS = [
    {
        "risk": "Tool failure",
        "example": "Booking database times out — agent hallucinates booking details instead of admitting it doesn't know",
        "mitigation": "Strict fallback instruction — if tool returns no result, say so, never infer. Retry max 3 times then escalate",
    },
    {
        "risk": "Wrong tool order",
        "example": "Refund eligibility called before booking lookup — missing input parameters, returns error",
        "mitigation": "Tool dependency map in agent prompt — explicitly define which tools depend on others",
    },
    {
        "risk": "Data leakage",
        "example": "Tool returns host payout details the AI wasn't supposed to see — surfaces in response",
        "mitigation": "Scope tool responses — each tool returns only fields the AI needs for that query type",
    },
    {
        "risk": "No MCP — direct DB access",
        "example": "AI has raw database access — one prompt injection attack exposes all customer data",
        "mitigation": "Always use middleware layer — MCP or equivalent — AI never touches database directly",
    },
]

def _simulate_airbnb_tools(profile):
    checkin = datetime.now() + timedelta(days=3)
    booking = {
        "booking_id": "BK-29471",
        "property": "Cozy Downtown Apartment",
        "check_in": checkin.strftime("%Y-%m-%d"),
        "nights": 3,
        "total_paid": 487.50,
        "nightly_rate": 145.00,
        "cleaning_fee": 52.50,
        "service_fee": 72.00,
        "policy": "moderate",
        "status": "confirmed",
    }
    refund = {
        "eligible": True,
        "refund_type": "partial_50",
        "refund_amount": 270.00,
        "days_until_checkin": 3,
        "policy_applied": "moderate",
        "note": "3 days < 5-day threshold. 50% of nightly rate refunded. Cleaning fee refunded in full. Service fee non-refundable.",
        "cleaning_fee_refundable": True,
        "service_fee_refundable": False,
    }
    return [
        {"tool": "lookup_booking", "latency": 94, "success": True, "output": booking},
        {"tool": "check_refund_eligibility", "latency": 108, "success": True, "output": refund},
    ]

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s08_tools"][domain]

    render_step_header("🔧", "Agentic Layer — Tool Execution",
        "The AI calls external systems to get real data.")

    render_thinking_card(content["thinking"])

    result = get_result("tools")

    if not result:
        with st.spinner("Calling tools..."):
            time.sleep(1.0)
            profile = st.session_state.profile or {}
            calls = _simulate_airbnb_tools(profile)
            result = {"calls": calls, "total_latency": sum(c["latency"] for c in calls)}
            store_result("tools", result)

    st.caption(f"⏱ Total: {result['total_latency']}ms")

    for call in result["calls"]:
        status = "✅" if call["success"] else "❌"
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"{status} **{call['tool']}**")
            with col2:
                st.caption(f"{call['latency']}ms")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("Output")
                st.json(call["output"], expanded=True)
            st.divider()

    with st.expander("Real MCP tool call — what travels between agent and server"):
        st.code("""{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "lookup_booking",
    "arguments": {"booking_id": "BK-29471", "user_id": "sarah_m_4821"}
  }
}

// MCP Server response — returns ONLY permitted fields
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": {
        "booking_id": "BK-29471",
        "check_in": "2024-05-03",
        "policy": "moderate",
        "total_paid": 487.50
      }
    }]
  }
}""", language="json")
        st.caption("Notice what's NOT returned — host payout, internal pricing, other users. MCP controls exactly what the AI sees.")

    render_what_we_built(
        "We built simulated tools that return realistic domain-specific data. The agent "
        "called them in sequence — first fetch the record, then check eligibility using "
        "what the record returned. In production these would be real API calls to live systems."
    )

    render_enterprise_note(
        "In production, tool calls go through MCP servers with OAuth tokens, API keys, "
        "and row-level security — the agent only sees data it's authorised for. "
        "Tool calls run in parallel where possible, reducing latency from 200ms to 80ms. "
        "Every tool call is logged for compliance and audited for data access patterns."
    )

    render_risk_table(RISKS)
    render_nav(back=True, next_label="Next: LLM Reasoning →")
