"""
Intent Classification Layer
Input  : raw user message
Output : intents, sentiment, urgency, routing, confidence scores
"""

import json
import time
from dataclasses import dataclass
from typing import Optional
from config.defaults import INTENT_LABELS, SENTIMENT_LABELS, URGENCY_LABELS

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
    used_llm: bool
    llm_reason: str

SYSTEM_PROMPT = """You are an intent classification system for a customer support AI.

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
  "used_llm": true,
  "llm_reason": "<why LLM was used instead of fast ML classifier>"
}}

Valid intents: {intent_labels}
Valid sentiments: {sentiment_labels}
Valid urgency: {urgency_labels}

Rules:
- Return ONLY valid JSON, no markdown, no explanation
- urgency critical = trip within 24 hours or safety issue
- urgency high = significant financial impact or trip within 72 hours
- out_of_scope if completely unrelated to support domain
"""

def classify_intent(message: str, llm_client, domain: str) -> IntentResult:
    start = time.time()
    prompt = SYSTEM_PROMPT.format(
        intent_labels=", ".join(INTENT_LABELS),
        sentiment_labels=", ".join(SENTIMENT_LABELS),
        urgency_labels=", ".join(URGENCY_LABELS),
    )
    try:
        response = llm_client.generate_content(f"{prompt}\n\nClassify: {message}")
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        return IntentResult(
            primary_intent=data.get("primary_intent", "general_inquiry"),
            primary_confidence=float(data.get("primary_confidence", 0.5)),
            secondary_intent=data.get("secondary_intent"),
            secondary_confidence=data.get("secondary_confidence"),
            sentiment=data.get("sentiment", "neutral"),
            sentiment_confidence=float(data.get("sentiment_confidence", 0.5)),
            urgency=data.get("urgency", "medium"),
            urgency_reason=data.get("urgency_reason", ""),
            all_scores=data.get("all_scores", {}),
            routing_suggestion=data.get("routing_suggestion", "standard_queue"),
            needs_tool_call=data.get("needs_tool_call", []),
            processing_time_ms=int((time.time() - start) * 1000),
            used_llm=data.get("used_llm", True),
            llm_reason=data.get("llm_reason", "LLM used for nuanced classification"),
        )
    except Exception as e:
        return IntentResult(
            primary_intent="general_inquiry",
            primary_confidence=0.4,
            secondary_intent=None,
            secondary_confidence=None,
            sentiment="neutral",
            sentiment_confidence=0.4,
            urgency="medium",
            urgency_reason=f"Fallback — parsing failed: {str(e)[:60]}",
            all_scores={},
            routing_suggestion="standard_queue",
            needs_tool_call=[],
            processing_time_ms=int((time.time() - start) * 1000),
            used_llm=True,
            llm_reason="Fallback values used due to parsing error",
        )
