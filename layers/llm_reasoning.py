"""
LLM Reasoning Layer
────────────────────
Input  : compiled context (intent + rag chunks + tools + system prompt)
Output : chain of thought, draft response, full context window (for inspection)

This is the most important layer to make transparent.
We show: what went in, how the LLM reasoned, what came out.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContextWindow:
    system_prompt: str
    intent_context: str
    tool_results: str
    rag_context: str
    user_message: str
    total_estimated_tokens: int

    def as_messages(self) -> list[dict]:
        """Assemble into LLM message format."""
        system = f"""{self.system_prompt}

━━━ INTENT ANALYSIS ━━━
{self.intent_context}

━━━ RETRIEVED POLICY CONTEXT ━━━
{self.rag_context}

━━━ TOOL RESULTS ━━━
{self.tool_results if self.tool_results else "No tools were called for this query."}
"""
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": self.user_message},
        ]


@dataclass
class ReasoningResult:
    chain_of_thought: str
    draft_response: str
    context_window: ContextWindow
    grounded: bool            # did response stay within retrieved context?
    grounding_note: str
    processing_time_ms: int
    model_used: str
    provider_used: str


REASONING_WITH_COT_PROMPT = """You are a customer support AI assistant. Think through the problem step by step before responding.

First, write your reasoning inside <thinking> tags:
- What is the user actually asking?
- What does the retrieved policy say about this?
- What can I say with confidence vs what is uncertain?
- What tone is appropriate given their sentiment?
- Should I escalate or can I resolve this?

Then write your final response to the user inside <response> tags.

Your response must:
- Be grounded ONLY in the retrieved policy context provided
- Never fabricate policy details
- Be empathetic and clear
- Indicate clearly if something requires human escalation
"""


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1.3 tokens per word."""
    return int(len(text.split()) * 1.3)


def _build_context_window(
    system_prompt: str,
    intent_result,
    rag_result,
    tool_results: dict,
    user_message: str,
) -> ContextWindow:
    """Assemble all layer outputs into the full context window."""

    intent_ctx = f"""Primary intent: {intent_result.primary_intent} (confidence: {intent_result.primary_confidence:.0%})
Secondary intent: {intent_result.secondary_intent or 'None'}
Sentiment: {intent_result.sentiment} (confidence: {intent_result.sentiment_confidence:.0%})
Urgency: {intent_result.urgency} — {intent_result.urgency_reason}
Routing: {intent_result.routing_suggestion}"""

    tool_ctx = ""
    if tool_results:
        for tool_name, result in tool_results.items():
            tool_ctx += f"\n[{tool_name}]\n{json.dumps(result, indent=2)}\n"

    rag_ctx = rag_result.context_text
    if rag_result.low_confidence_warning:
        rag_ctx = f"⚠️ LOW CONFIDENCE RETRIEVAL: {rag_result.warning_message}\n\n{rag_ctx}"

    # Full system prompt for reasoning includes our CoT instruction
    full_system = f"{REASONING_WITH_COT_PROMPT}\n\n{system_prompt}"

    total_tokens = (
        _estimate_tokens(full_system)
        + _estimate_tokens(intent_ctx)
        + _estimate_tokens(tool_ctx)
        + _estimate_tokens(rag_ctx)
        + _estimate_tokens(user_message)
    )

    return ContextWindow(
        system_prompt=full_system,
        intent_context=intent_ctx,
        tool_results=tool_ctx,
        rag_context=rag_ctx,
        user_message=user_message,
        total_estimated_tokens=total_tokens,
    )


def _parse_cot_response(raw: str) -> tuple[str, str]:
    """Extract chain of thought and final response from tagged output."""
    cot = ""
    response = ""

    if "<thinking>" in raw and "</thinking>" in raw:
        cot = raw.split("<thinking>")[1].split("</thinking>")[0].strip()

    if "<response>" in raw and "</response>" in raw:
        response = raw.split("<response>")[1].split("</response>")[0].strip()
    elif "</thinking>" in raw:
        # Fallback: everything after thinking is the response
        response = raw.split("</thinking>")[-1].strip()
    else:
        response = raw.strip()

    return cot, response


def _check_grounding(response: str, rag_context: str) -> tuple[bool, str]:
    """
    Simple grounding check — did the response stay within retrieved content?
    Full grounding check happens in guardrails, this is a quick signal.
    """
    # If response is very long relative to context, flag it
    if len(response) > len(rag_context) * 0.8 and len(rag_context) < 200:
        return False, "Response may exceed retrieved context — possible elaboration beyond policy"

    # Check for specific numbers/policies that weren't in context
    import re
    response_numbers = set(re.findall(r'\$[\d,]+|\d+%|\d+ days|\d+ hours', response))
    context_numbers = set(re.findall(r'\$[\d,]+|\d+%|\d+ days|\d+ hours', rag_context))
    ungrounded = response_numbers - context_numbers

    if ungrounded:
        return False, f"Contains specific values not found in retrieved context: {ungrounded}"

    return True, "Response appears grounded in retrieved context"


def _call_llm(messages: list[dict], llm_client, provider: str, model: str, temperature: float) -> str:
    if provider == "openai":
        response = llm_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    elif provider == "anthropic":
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        response = llm_client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=user_msgs,
            temperature=temperature,
        )
        return response.content[0].text

    elif provider == "gemini":
        full_prompt = "\n\n".join(m["content"] for m in messages)
        response = llm_client.generate_content(full_prompt)
        return response.text

    raise ValueError(f"Unknown provider: {provider}")


def reason(
    user_message: str,
    intent_result,
    rag_result,
    tool_results: dict,
    system_prompt: str,
    llm_client,
    provider: str,
    model: str,
    temperature: float = 0.2,
) -> ReasoningResult:
    """
    Main reasoning function.
    Assembles context, calls LLM with chain-of-thought, returns full transparency output.
    """
    start = time.time()

    # Build full context window
    ctx = _build_context_window(
        system_prompt=system_prompt,
        intent_result=intent_result,
        rag_result=rag_result,
        tool_results=tool_results,
        user_message=user_message,
    )

    # Call LLM
    messages = ctx.as_messages()
    raw_output = _call_llm(messages, llm_client, provider, model, temperature)

    # Parse chain of thought + response
    cot, draft = _parse_cot_response(raw_output)

    # Grounding check
    grounded, grounding_note = _check_grounding(draft, rag_result.context_text)

    processing_time = int((time.time() - start) * 1000)

    return ReasoningResult(
        chain_of_thought=cot,
        draft_response=draft,
        context_window=ctx,
        grounded=grounded,
        grounding_note=grounding_note,
        processing_time_ms=processing_time,
        model_used=model,
        provider_used=provider,
    )
