"""Step 3 — Query input: recommended queries + free text."""
import streamlit as st
from config.defaults import RECOMMENDED_QUERIES
from config.content import DOMAIN_LABELS, DOMAIN_ICONS
from ui import render_topbar, render_step_header, render_nav

def render():
    render_topbar()
    domain = st.session_state.domain
    icon = DOMAIN_ICONS.get(domain, "🤖")
    label = DOMAIN_LABELS.get(domain, "")

    render_step_header("💬", "What do you need help with?",
        f"You're talking to the {icon} {label} support bot.")

    # Recommended queries
    st.markdown("**Try one of these — or type your own:**")
    queries = RECOMMENDED_QUERIES.get(domain, [])

    # 2-column grid of example buttons
    cols = st.columns(2)
    for i, q in enumerate(queries):
        with cols[i % 2]:
            if st.button(q, key=f"q_{i}", use_container_width=True):
                st.session_state.query = q
                st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Free text input
    user_query = st.text_area(
        "Or type your own question:",
        value=st.session_state.query or "",
        height=80,
        placeholder="Type anything you'd say to a real support agent...",
        label_visibility="visible",
    )

    if user_query != st.session_state.query:
        st.session_state.query = user_query

    # Profile reminder
    if st.session_state.profile:
        p = st.session_state.profile
        trust_color = "#1D9E75" if p["trust_score"] >= 70 else "#BA7517" if p["trust_score"] >= 40 else "#E24B4A"
        st.markdown(f"""
<div style="font-size:11px;color:var(--color-text-tertiary);margin-top:8px">
Logged in as <strong style="color:var(--color-text-secondary)">{p["name"]}</strong> · 
Trust score: <strong style="color:{trust_color}">{p["trust_score"]}/100</strong>
</div>
""", unsafe_allow_html=True)

    render_nav(
        back=True,
        next_label="Submit →",
        next_disabled=not bool(st.session_state.query and st.session_state.query.strip()),
    )
