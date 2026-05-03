"""
Behind The Bot
───────────────
See what happens between send and reply.

Run: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Behind The Bot",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit chrome for cleaner experience
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 800px;}
</style>
""", unsafe_allow_html=True)

from state import init_state
init_state()

from ui import render_key_prompt
from state import needs_key_prompt

# Route to correct step
step = st.session_state.step

if step == "landing":
    from steps.s01_landing import render; render()

elif step == "login":
    from steps.s02_login import render; render()

elif step == "query":
    from steps.s03_query import render; render()

elif step == "input_guardrails":
    if needs_key_prompt():
        render_key_prompt()
    else:
        from steps.s04_input_guardrails import render; render()

elif step == "intent":
    if needs_key_prompt():
        render_key_prompt()
    else:
        from steps.s05_intent import render; render()

elif step == "agentic_intro":
    from steps.s06_agentic_intro import render; render()

elif step == "rag":
    from steps.s07_rag import render; render()

elif step == "tools":
    from steps.s08_tools import render; render()

elif step == "reasoning":
    if needs_key_prompt():
        render_key_prompt()
    else:
        from steps.s09_reasoning import render; render()

elif step == "output_guardrails":
    from steps.s10_output_guardrails import render; render()

elif step == "response":
    from steps.s11_response import render; render()

elif step == "judge":
    if needs_key_prompt():
        render_key_prompt()
    else:
        from steps.s11b_judge import render; render()

elif step == "observability":
    from steps.s12_observability import render; render()
    # Reset for next run
    if st.button("🔄 Start a new run", use_container_width=False):
        st.session_state.clear()
        st.rerun()
