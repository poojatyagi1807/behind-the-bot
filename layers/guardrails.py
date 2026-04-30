"""
Guardrails Layer
─────────────────
Input  : draft response from LLM + full context
Output : each guardrail's result (pass/fail/modified), final response

Every check is made visible — PMs can see exactly which guardrail fired,
what it caught, and whether it modified or blocked the response.
"""

import time
import re
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GuardrailCheck:
    name: str
    description: str
    status: str          # "pass", "fail", "modified", "skipped"
    severity: str        # "high", "medium", "low"
    finding: str         # what it found (or "Clean" if pass)
    action_taken: str    # "none", "blocked", "modified", "escalation_added"
    enabled: bool


@dataclass
class GuardrailResult:
    original_response: str
    final_response: str
    checks: list[GuardrailCheck]
    overall_status: str    # "pass", "modified", "blocked"
    was_modified: bool
    was_blocked: bool
    escalation_added: bool
    processing_time_ms: int
    summary: str


# ── Individual guardrail functions ────────────────────────────────────────────

def _check_hallucination(
    response: str,
    rag_context: str,
    llm_client,
    provider: str,
    model: str,
    enabled: bool,
) -> GuardrailCheck:
    """Use LLM to check if response contains claims not in retrieved context."""

    if not enabled:
        return GuardrailCheck(
            name="No hallucination",
            description="Response must only contain claims supported by retrieved context",
            status="skipped", severity="high",
            finding="Guardrail disabled", action_taken="none", enabled=False,
        )

    prompt = f"""You are a hallucination detector. 

Retrieved context:
{rag_context[:2000]}

Response to check:
{response}

Does the response contain any specific claims (numbers, policy details, timelines, amounts) that are NOT supported by the retrieved context?

Reply with JSON only:
{{"hallucination_detected": true/false, "finding": "description of what was found or Clean"}}"""

    try:
        raw = _quick_llm_call(prompt, llm_client, provider, model)
        data = json.loads(raw.strip().strip("```json").strip("```"))
        detected = data.get("hallucination_detected", False)
        finding = data.get("finding", "Clean")

        return GuardrailCheck(
            name="No hallucination",
            description="Response must only contain claims supported by retrieved context",
            status="fail" if detected else "pass",
            severity="high",
            finding=finding,
            action_taken="blocked" if detected else "none",
            enabled=True,
        )
    except Exception as e:
        return GuardrailCheck(
            name="No hallucination",
            description="Response must only contain claims supported by retrieved context",
            status="pass",  # fail open on guardrail error
            severity="high",
            finding=f"Check error (failing open): {str(e)[:100]}",
            action_taken="none",
            enabled=True,
        )


def _check_pii(response: str, enabled: bool) -> GuardrailCheck:
    """Regex-based PII detection — fast, no LLM call needed."""
    if not enabled:
        return GuardrailCheck(
            name="No PII exposure",
            description="Response must not expose personal or financial data",
            status="skipped", severity="high",
            finding="Guardrail disabled", action_taken="none", enabled=False,
        )

    pii_patterns = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        "bank_account": r'\baccount\s+(?:number|#|no\.?)\s*:?\s*\d{6,}\b',
    }

    found = []
    for label, pattern in pii_patterns.items():
        matches = re.findall(pattern, response, re.IGNORECASE)
        if matches:
            found.append(f"{label}: {len(matches)} instance(s)")

    if found:
        return GuardrailCheck(
            name="No PII exposure",
            description="Response must not expose personal or financial data",
            status="fail", severity="high",
            finding=f"PII detected: {', '.join(found)}",
            action_taken="blocked",
            enabled=True,
        )

    return GuardrailCheck(
        name="No PII exposure",
        description="Response must not expose personal or financial data",
        status="pass", severity="high",
        finding="Clean — no PII patterns detected",
        action_taken="none",
        enabled=True,
    )


def _check_policy_compliance(
    response: str,
    rag_context: str,
    intent_result,
    llm_client,
    provider: str,
    model: str,
    enabled: bool,
) -> GuardrailCheck:
    """Check that any policy decisions align with retrieved policy."""
    if not enabled:
        return GuardrailCheck(
            name="Policy compliance",
            description="Any decision must align with retrieved policy",
            status="skipped", severity="high",
            finding="Guardrail disabled", action_taken="none", enabled=False,
        )

    prompt = f"""You are a policy compliance checker for a customer support system.

Retrieved policy:
{rag_context[:2000]}

Support response:
{response}

Check: Does the response make any policy decisions (refund approvals, cancellation rulings, eligibility determinations) that CONTRADICT the retrieved policy?

Reply with JSON only:
{{"violation_detected": true/false, "finding": "specific violation or Clean"}}"""

    try:
        raw = _quick_llm_call(prompt, llm_client, provider, model)
        data = json.loads(raw.strip().strip("```json").strip("```"))
        violated = data.get("violation_detected", False)
        finding = data.get("finding", "Clean")

        return GuardrailCheck(
            name="Policy compliance",
            description="Any decision must align with retrieved policy",
            status="fail" if violated else "pass",
            severity="high",
            finding=finding,
            action_taken="blocked" if violated else "none",
            enabled=True,
        )
    except Exception as e:
        return GuardrailCheck(
            name="Policy compliance",
            description="Any decision must align with retrieved policy",
            status="pass",
            severity="high",
            finding=f"Check error (failing open): {str(e)[:100]}",
            action_taken="none",
            enabled=True,
        )


def _check_escalation(
    response: str,
    intent_result,
    enabled: bool,
) -> tuple[GuardrailCheck, str]:
    """Add escalation note if routing says human_escalation but response doesn't mention it."""
    if not enabled:
        return GuardrailCheck(
            name="Escalation trigger",
            description="Complex/low-confidence queries should suggest human escalation",
            status="skipped", severity="medium",
            finding="Guardrail disabled", action_taken="none", enabled=False,
        ), response

    should_escalate = (
        getattr(intent_result, 'routing_suggestion', '') == 'human_escalation'
        or getattr(intent_result, 'urgency', '') == 'critical'
    )

    escalation_keywords = ["human agent", "escalat", "specialist", "representative", "transfer"]
    already_escalates = any(kw in response.lower() for kw in escalation_keywords)

    if should_escalate and not already_escalates:
        modified = response + "\n\n*This case has been flagged for review by a human support agent who will follow up with you shortly.*"
        return GuardrailCheck(
            name="Escalation trigger",
            description="Complex/low-confidence queries should suggest human escalation",
            status="modified", severity="medium",
            finding=f"Routing was '{intent_result.routing_suggestion}' but response lacked escalation note",
            action_taken="modified",
            enabled=True,
        ), modified

    return GuardrailCheck(
        name="Escalation trigger",
        description="Complex/low-confidence queries should suggest human escalation",
        status="pass", severity="medium",
        finding="Clean — escalation handled appropriately",
        action_taken="none",
        enabled=True,
    ), response


def _check_tone(
    response: str,
    llm_client,
    provider: str,
    model: str,
    enabled: bool,
) -> GuardrailCheck:
    """Quick tone check — is the response empathetic and professional?"""
    if not enabled:
        return GuardrailCheck(
            name="Tone check",
            description="Response must be empathetic and professional",
            status="skipped", severity="low",
            finding="Guardrail disabled", action_taken="none", enabled=False,
        )

    prompt = f"""Check if this customer support response is empathetic and professional.
    
Response: {response[:500]}

Reply with JSON only:
{{"tone_issue": true/false, "finding": "issue description or Clean"}}"""

    try:
        raw = _quick_llm_call(prompt, llm_client, provider, model)
        data = json.loads(raw.strip().strip("```json").strip("```"))
        issue = data.get("tone_issue", False)
        finding = data.get("finding", "Clean")

        return GuardrailCheck(
            name="Tone check",
            description="Response must be empathetic and professional",
            status="fail" if issue else "pass",
            severity="low",
            finding=finding,
            action_taken="none",  # tone issues flag but don't block
            enabled=True,
        )
    except Exception:
        return GuardrailCheck(
            name="Tone check",
            description="Response must be empathetic and professional",
            status="pass",
            severity="low",
            finding="Check skipped (non-critical)",
            action_taken="none",
            enabled=True,
        )


def _quick_llm_call(prompt: str, llm_client, provider: str, model: str) -> str:
    """Fast LLM call for guardrail checks — low token usage."""
    if provider == "openai":
        response = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    elif provider == "anthropic":
        response = llm_client.messages.create(
            model=model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return response.content[0].text

    elif provider == "gemini":
        response = llm_client.generate_content(prompt)
        return response.text

    raise ValueError(f"Unknown provider: {provider}")


# ── Main guardrails runner ─────────────────────────────────────────────────────

def run_guardrails(
    draft_response: str,
    rag_result,
    intent_result,
    guardrail_configs: list[dict],
    llm_client,
    provider: str,
    model: str,
) -> GuardrailResult:
    """
    Run all enabled guardrails in sequence.
    High-severity fails block. Medium/low modify or flag.
    """
    start = time.time()

    checks = []
    current_response = draft_response
    was_blocked = False
    escalation_added = False

    # Build enabled map from config
    enabled = {g["name"]: g["enabled"] for g in guardrail_configs}

    # 1. PII check (fast, no LLM)
    pii_check = _check_pii(
        current_response,
        enabled.get("No PII exposure", True),
    )
    checks.append(pii_check)
    if pii_check.status == "fail" and pii_check.severity == "high":
        current_response = "[Response blocked: PII detected in draft. A human agent will follow up.]"
        was_blocked = True

    # 2. Hallucination check
    if not was_blocked:
        hall_check = _check_hallucination(
            current_response,
            rag_result.context_text,
            llm_client, provider, model,
            enabled.get("No hallucination", True),
        )
        checks.append(hall_check)
        if hall_check.status == "fail" and hall_check.severity == "high":
            current_response = (
                "I want to make sure I give you accurate information. "
                "Let me connect you with a human support agent who can review the details of your case directly."
            )
            was_blocked = True

    # 3. Policy compliance check
    if not was_blocked:
        policy_check = _check_policy_compliance(
            current_response,
            rag_result.context_text,
            intent_result,
            llm_client, provider, model,
            enabled.get("Policy compliance", True),
        )
        checks.append(policy_check)
        if policy_check.status == "fail":
            current_response = (
                "I want to provide you with accurate policy information. "
                "Based on what I can see, let me connect you with a specialist who can confirm the details."
            )
            was_blocked = True

    # 4. Escalation trigger (may modify response)
    if not was_blocked:
        esc_check, current_response = _check_escalation(
            current_response,
            intent_result,
            enabled.get("Escalation trigger", True),
        )
        checks.append(esc_check)
        if esc_check.status == "modified":
            escalation_added = True

    # 5. Tone check (flags only, doesn't block)
    if not was_blocked:
        tone_check = _check_tone(
            current_response,
            llm_client, provider, model,
            enabled.get("Tone check", True),
        )
        checks.append(tone_check)

    # Summary
    failed = [c for c in checks if c.status == "fail"]
    modified = [c for c in checks if c.status == "modified"]

    if was_blocked:
        overall = "blocked"
        summary = f"Response blocked by {failed[0].name if failed else 'guardrail'}. Safe fallback served."
    elif modified:
        overall = "modified"
        summary = f"Response passed with {len(modified)} modification(s): {', '.join(c.name for c in modified)}"
    else:
        overall = "pass"
        summary = f"All {len(checks)} guardrails passed."

    processing_time = int((time.time() - start) * 1000)

    was_modified = current_response != draft_response and not was_blocked

    return GuardrailResult(
        original_response=draft_response,
        final_response=current_response,
        checks=checks,
        overall_status=overall,
        was_modified=was_modified,
        was_blocked=was_blocked,
        escalation_added=escalation_added,
        processing_time_ms=processing_time,
        summary=summary,
    )
