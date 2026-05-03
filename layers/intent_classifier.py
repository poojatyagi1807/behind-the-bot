"""
Intent Classification Layer — Two-stage cascade
─────────────────────────────────────────────────
Stage 1: ML classifier (TF-IDF + Logistic Regression) — <5ms
Stage 2: LLM classifier (Gemini) — only if ML confidence < 0.75

Shows students exactly how enterprise cascades work.
"""

import json
import time
from dataclasses import dataclass
from typing import Optional
from config.defaults import INTENT_LABELS, SENTIMENT_LABELS, URGENCY_LABELS
from layers.ml_classifier import get_classifier


@dataclass
class IntentResult:
    primary_intent: str
    primary_confidence: float
    secondary_intent: Optional[str]
    secondary_confidence: Optional[float]
    sentiment: str
    sentiment_confidence: float
    urgency: str
    urgency_reason: str
    all_scores: dict
    routing_suggestion: str
    needs_tool_call: list
    processing_time_ms: int
    ml_processing_time_ms: int
    llm_processing_time_ms: int
    used_llm: bool
    llm_reason: str
    ml_confidence: float


LLM_SYSTEM_PROMPT = """You are an intent classification system for a customer support AI.

The fast ML classifier ran first but had LOW CONFIDENCE. You need to make a more nuanced classification.

Analyze the user message and return a JSON object with EXACTLY this structure:
{{
  "primary_intent": "<one of the valid intents>",
  "primary_confidence": <0.0 to 1.0>,
  "secondary_intent": "<one of the valid intents or null>",
  "secondary_confidence": <0.0 to 1.0 or null>,
  "sentiment": "<one of the valid sentiments>",
  "sentiment_confidence": <0.0 to 1.0>,
  "urgency": "<one of the valid urgency levels>",
  "urgency_reason": "<one sentence>",
  "all_scores": {{"cancellation_request": 0.0, "refund_request": 0.0, "booking_inquiry": 0.0, "complaint": 0.0, "policy_question": 0.0, "escalation_request": 0.0, "general_inquiry": 0.0, "out_of_scope": 0.0}},
  "routing_suggestion": "<standard_queue, priority_queue, human_escalation, or out_of_scope>",
  "needs_tool_call": ["tool_id_1"],
  "llm_reason": "<why this classification requires LLM nuance>"
}}

Valid intents: {intent_labels}
Valid sentiments: {sentiment_labels}
Valid urgency: {urgency_labels}

Rules:
- Return ONLY valid JSON, no markdown
- urgency critical = trip within 24 hours or safety issue
- urgency high = significant financial impact or within 72 hours
"""


def _call_llm(message: str, llm_client) -> dict:
    """LLM classification — only invoked when ML confidence is low."""
    prompt = LLM_SYSTEM_PROMPT.format(
        intent_labels=", ".join(INTENT_LABELS),
        sentiment_labels=", ".join(SENTIMENT_LABELS),
        urgency_labels=", ".join(URGENCY_LABELS),
    )
    response = llm_client.generate_content(f"{prompt}\n\nClassify: {message}")
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def classify_intent(message: str, llm_client, domain: str) -> IntentResult:
    """
    Two-stage cascade:
    1. Fast ML classifier — always runs first
    2. LLM — only if ML confidence < 0.75
    """
    total_start = time.time()

    # ── Stage 1: ML classifier ────────────────────────────────────────────────
    ml_start = time.time()
    classifier = get_classifier()
    ml_result = classifier.classify(message)
    ml_time = int((time.time() - ml_start) * 1000)

    used_llm = False
    llm_time = 0
    llm_reason = ml_result["ml_reason"]

    # ── Stage 2: LLM (only if needed) ────────────────────────────────────────
    if ml_result["should_invoke_llm"] and llm_client:
        try:
            llm_start = time.time()
            llm_data = _call_llm(message, llm_client)
            llm_time = int((time.time() - llm_start) * 1000)
            used_llm = True
            llm_reason = llm_data.get("llm_reason", "LLM used for nuanced classification")

            # LLM result overrides ML result
            return IntentResult(
                primary_intent=llm_data.get("primary_intent", ml_result["primary_intent"]),
                primary_confidence=float(llm_data.get("primary_confidence", ml_result["primary_confidence"])),
                secondary_intent=llm_data.get("secondary_intent"),
                secondary_confidence=llm_data.get("secondary_confidence"),
                sentiment=llm_data.get("sentiment", "neutral"),
                sentiment_confidence=float(llm_data.get("sentiment_confidence", 0.5)),
                urgency=llm_data.get("urgency", "medium"),
                urgency_reason=llm_data.get("urgency_reason", ""),
                all_scores=llm_data.get("all_scores", ml_result["all_scores"]),
                routing_suggestion=llm_data.get("routing_suggestion", "standard_queue"),
                needs_tool_call=llm_data.get("needs_tool_call", []),
                processing_time_ms=int((time.time() - total_start) * 1000),
                ml_processing_time_ms=ml_time,
                llm_processing_time_ms=llm_time,
                used_llm=True,
                llm_reason=llm_reason,
                ml_confidence=ml_result["primary_confidence"],
            )
        except Exception:
            pass  # Fall through to ML result if LLM fails

    # ── ML result sufficient ──────────────────────────────────────────────────
    # Derive sentiment and urgency from ML result heuristically
    message_lower = message.lower()

    if any(w in message_lower for w in ["urgent", "emergency", "immediately", "asap", "right now", "hours"]):
        urgency = "high"
        urgency_reason = "Urgency keywords detected in message"
    elif any(w in message_lower for w in ["tomorrow", "tonight", "today", "soon"]):
        urgency = "medium"
        urgency_reason = "Near-term timing signals detected"
    else:
        urgency = "low"
        urgency_reason = "No immediate time pressure detected"

    if any(w in message_lower for w in ["furious", "outraged", "disgusting", "unacceptable", "terrible", "horrible"]):
        sentiment = "angry"
        sentiment_confidence = 0.85
    elif any(w in message_lower for w in ["frustrated", "disappointed", "unhappy", "upset"]):
        sentiment = "frustrated"
        sentiment_confidence = 0.80
    elif any(w in message_lower for w in ["confused", "unsure", "not sure", "wondering"]):
        sentiment = "confused"
        sentiment_confidence = 0.75
    else:
        sentiment = "neutral"
        sentiment_confidence = 0.70

    routing = "standard_queue"
    if ml_result["primary_intent"] == "escalation_request" or urgency == "high":
        routing = "human_escalation"
    elif ml_result["primary_intent"] == "out_of_scope":
        routing = "out_of_scope"
    elif urgency == "medium":
        routing = "priority_queue"

    needs_tools = []
    if ml_result["primary_intent"] in ("cancellation_request", "refund_request"):
        needs_tools = ["lookup_booking", "check_refund_eligibility"]
    elif ml_result["primary_intent"] == "complaint":
        needs_tools = ["lookup_booking", "create_support_ticket"]
    elif ml_result["primary_intent"] == "escalation_request":
        needs_tools = ["create_support_ticket"]

    return IntentResult(
        primary_intent=ml_result["primary_intent"],
        primary_confidence=ml_result["primary_confidence"],
        secondary_intent=ml_result["secondary_intent"],
        secondary_confidence=ml_result["secondary_confidence"],
        sentiment=sentiment,
        sentiment_confidence=sentiment_confidence,
        urgency=urgency,
        urgency_reason=urgency_reason,
        all_scores=ml_result["all_scores"],
        routing_suggestion=routing,
        needs_tool_call=needs_tools,
        processing_time_ms=int((time.time() - total_start) * 1000),
        ml_processing_time_ms=ml_time,
        llm_processing_time_ms=llm_time,
        used_llm=False,
        llm_reason=llm_reason,
        ml_confidence=ml_result["primary_confidence"],
    )
