"""
State manager — single source of truth for the guided flow.
Manages step progression, accumulated results, error recovery,
free run limit, and API key state.
"""

import streamlit as st
import time
from config.defaults import FREE_RUNS_ALLOWED, GEMINI_MODEL

STEPS = [
    "landing",
    "login",
    "query",
    "input_guardrails",
    "intent",
    "agentic_intro",
    "rag",
    "tools",
    "reasoning",
    "output_guardrails",
    "response",
    "judge",
    "observability",
]

def init_state():
    """Initialise all session state on first load."""
    defaults = {
        "step": "landing",
        "domain": None,
        "profile": None,
        "query": None,
        "api_key": None,
        "free_runs_used": 0,
        "llm_client": None,
        "doc_text": None,
        "results": {},
        "errors": {},
        "step_times": {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def go_to(step: str):
    st.session_state.step = step
    st.rerun()

def go_next():
    current = st.session_state.step
    if current in STEPS:
        idx = STEPS.index(current)
        if idx < len(STEPS) - 1:
            st.session_state.step = STEPS[idx + 1]
            st.rerun()

def go_back():
    current = st.session_state.step
    if current in STEPS:
        idx = STEPS.index(current)
        if idx > 0:
            st.session_state.step = STEPS[idx - 1]
            st.rerun()

def store_result(step: str, result):
    st.session_state.results[step] = result

def get_result(step: str):
    return st.session_state.results.get(step)

def store_error(step: str, error: str):
    st.session_state.errors[step] = error

def get_llm_client():
    """Get or create Gemini client."""
    if st.session_state.llm_client:
        return st.session_state.llm_client
    key = st.session_state.api_key or st.secrets.get("GEMINI_API_KEY", None)
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        client = genai.GenerativeModel(GEMINI_MODEL)
        st.session_state.llm_client = client
        return client
    except Exception:
        return None

def has_free_run():
    return st.session_state.free_runs_used < FREE_RUNS_ALLOWED

def use_free_run():
    st.session_state.free_runs_used += 1

def has_api_key():
    return bool(st.session_state.api_key) or bool(st.secrets.get("GEMINI_API_KEY", None))

def needs_key_prompt():
    """True if free runs exhausted and no personal key."""
    return (
        st.session_state.free_runs_used >= FREE_RUNS_ALLOWED
        and not st.session_state.api_key
    )

def current_step_index():
    step = st.session_state.step
    return STEPS.index(step) if step in STEPS else 0

def progress_pct():
    return current_step_index() / (len(STEPS) - 1)
