"""
Tool Execution Layer (Simulated)
──────────────────────────────────
Simulates database and API calls that a real system would make.
Every tool call is logged with input, output, and latency for visualization.

In a real system these would call actual APIs.
Here they return realistic simulated data so the demo works without dependencies.
"""

import time
import random
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ToolCall:
    tool_id: str
    tool_name: str
    input_params: dict
    output: dict
    success: bool
    error: str
    latency_ms: int
    simulated: bool = True


@dataclass
class ToolExecutionResult:
    calls: list[ToolCall]
    compiled_results: dict   # merged results for LLM context
    total_latency_ms: int
    any_failed: bool
    failure_summary: str


# ── Simulated tool implementations ────────────────────────────────────────────

def _simulate_lookup_booking(params: dict) -> dict:
    """Return realistic booking data."""
    time.sleep(0.05)  # simulate network latency
    return {
        "booking_id": params.get("booking_id", "BK-29471"),
        "guest_name": "User",
        "property": "Cozy Downtown Apartment",
        "check_in": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
        "check_out": (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d"),
        "nights": 3,
        "total_paid": 487.50,
        "nightly_rate": 145.00,
        "cleaning_fee": 52.50,
        "service_fee": 72.00,
        "currency": "USD",
        "status": "confirmed",
        "cancellation_policy": "moderate",
        "account_age_days": 412,
        "prior_cancellations": 0,
    }


def _simulate_check_refund_eligibility(params: dict) -> dict:
    """Calculate refund based on policy and timing."""
    time.sleep(0.08)
    policy = params.get("cancellation_policy", "moderate")
    days_until_checkin = params.get("days_until_checkin", 3)

    eligibility = {
        "flexible": {
            "full_refund_if_days_gte": 1,
            "partial_refund_if_days_gte": 0,
            "no_refund_threshold": 0,
        },
        "moderate": {
            "full_refund_if_days_gte": 5,
            "partial_refund_if_days_gte": 1,
            "no_refund_threshold": 0,
        },
        "strict": {
            "full_refund_if_days_gte": 14,
            "partial_refund_if_days_gte": 7,
            "no_refund_threshold": 7,
        },
    }

    rules = eligibility.get(policy, eligibility["moderate"])
    total = params.get("total_paid", 487.50)
    nightly = params.get("nightly_rate", 145.00)
    cleaning = params.get("cleaning_fee", 52.50)
    service = params.get("service_fee", 72.00)

    if days_until_checkin >= rules["full_refund_if_days_gte"]:
        refund_amount = total
        refund_type = "full"
        note = f"Full refund eligible — {days_until_checkin} days until check-in meets {rules['full_refund_if_days_gte']}-day threshold for {policy} policy."
    elif days_until_checkin >= rules["partial_refund_if_days_gte"] and rules["partial_refund_if_days_gte"] > 0:
        refund_amount = round(total * 0.5, 2)
        refund_type = "partial_50"
        note = f"Partial 50% refund eligible — {days_until_checkin} days until check-in falls in partial window for {policy} policy."
    else:
        refund_amount = 0.0
        refund_type = "none"
        note = f"No refund eligible — {days_until_checkin} days until check-in is within non-refundable window for {policy} policy."

    return {
        "eligible": refund_type != "none",
        "refund_type": refund_type,
        "refund_amount": refund_amount,
        "policy_applied": policy,
        "days_until_checkin": days_until_checkin,
        "note": note,
        "cleaning_fee_refundable": refund_type == "full",
        "service_fee_refundable": policy == "flexible",
    }


def _simulate_get_cancellation_policy(params: dict) -> dict:
    """Return the host's selected policy details."""
    time.sleep(0.04)
    policy_name = params.get("policy_name", "moderate")

    policies = {
        "flexible": {
            "name": "Flexible",
            "full_refund_window": "24 hours before check-in",
            "cleaning_fee_refund": "Yes, if cancelled before check-in",
            "service_fee_refund": "First cancellation only",
        },
        "moderate": {
            "name": "Moderate",
            "full_refund_window": "5 days before check-in",
            "partial_refund": "50% for 1-5 days before check-in",
            "cleaning_fee_refund": "Yes, if cancelled before check-in",
            "service_fee_refund": "No",
        },
        "strict": {
            "name": "Strict",
            "full_refund_window": "14 days before check-in",
            "partial_refund": "25% for 7-14 days before check-in",
            "cleaning_fee_refund": "No",
            "service_fee_refund": "No",
        },
    }

    return policies.get(policy_name, policies["moderate"])


def _simulate_create_support_ticket(params: dict) -> dict:
    """Create a simulated support ticket."""
    time.sleep(0.06)
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    return {
        "ticket_id": ticket_id,
        "status": "created",
        "priority": params.get("priority", "normal"),
        "estimated_response": "2-4 business hours",
        "message": f"Ticket {ticket_id} created. A human agent will review your case.",
    }


def _simulate_process_refund(params: dict) -> dict:
    """Simulate refund processing — disabled by default."""
    time.sleep(0.1)
    return {
        "refund_id": f"REF-{random.randint(100000, 999999)}",
        "amount": params.get("amount", 0),
        "status": "initiated",
        "estimated_arrival": "5-10 business days",
        "payment_method": "Original payment method",
    }


# ── Tool dispatcher ────────────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "lookup_booking": _simulate_lookup_booking,
    "check_refund_eligibility": _simulate_check_refund_eligibility,
    "get_cancellation_policy": _simulate_get_cancellation_policy,
    "create_support_ticket": _simulate_create_support_ticket,
    "process_refund": _simulate_process_refund,
}

TOOL_NAMES = {
    "lookup_booking": "Look up booking",
    "check_refund_eligibility": "Check refund eligibility",
    "get_cancellation_policy": "Get cancellation policy",
    "create_support_ticket": "Create support ticket",
    "process_refund": "Process refund",
}


def execute_tools(
    needed_tools: list[str],
    enabled_tools: list[str],
    booking_context: dict = None,
) -> ToolExecutionResult:
    """
    Execute the tools identified by intent classifier.
    Only runs tools that are enabled in the current session config.

    Returns full execution log for visualization.
    """
    start = time.time()
    calls = []
    compiled = {}
    any_failed = False
    failed_names = []

    for tool_id in needed_tools:
        if tool_id not in enabled_tools:
            # Tool exists but is disabled — log it
            calls.append(ToolCall(
                tool_id=tool_id,
                tool_name=TOOL_NAMES.get(tool_id, tool_id),
                input_params={},
                output={},
                success=False,
                error=f"Tool '{tool_id}' is disabled in current configuration",
                latency_ms=0,
            ))
            continue

        if tool_id not in TOOL_FUNCTIONS:
            continue

        tool_fn = TOOL_FUNCTIONS[tool_id]

        # Build params from booking context
        params = booking_context.copy() if booking_context else {}
        if tool_id == "check_refund_eligibility" and "cancellation_policy" in compiled.get("lookup_booking", {}):
            params.update(compiled["lookup_booking"])
            from datetime import datetime
            try:
                checkin = datetime.strptime(compiled["lookup_booking"]["check_in"], "%Y-%m-%d")
                params["days_until_checkin"] = max(0, (checkin - datetime.now()).days)
            except Exception:
                params["days_until_checkin"] = 3

        tool_start = time.time()
        try:
            result = tool_fn(params)
            latency = int((time.time() - tool_start) * 1000)
            calls.append(ToolCall(
                tool_id=tool_id,
                tool_name=TOOL_NAMES.get(tool_id, tool_id),
                input_params=params,
                output=result,
                success=True,
                error="",
                latency_ms=latency,
            ))
            compiled[tool_id] = result

        except Exception as e:
            latency = int((time.time() - tool_start) * 1000)
            any_failed = True
            failed_names.append(TOOL_NAMES.get(tool_id, tool_id))
            calls.append(ToolCall(
                tool_id=tool_id,
                tool_name=TOOL_NAMES.get(tool_id, tool_id),
                input_params=params,
                output={},
                success=False,
                error=str(e),
                latency_ms=latency,
            ))

    total_latency = int((time.time() - start) * 1000)
    failure_summary = f"Tools failed: {', '.join(failed_names)}" if failed_names else ""

    return ToolExecutionResult(
        calls=calls,
        compiled_results=compiled,
        total_latency_ms=total_latency,
        any_failed=any_failed,
        failure_summary=failure_summary,
    )
