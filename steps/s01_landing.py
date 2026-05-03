"""Step 1 — Landing: auto-set Airbnb and go straight to login."""
import streamlit as st
from state import go_to

def render():
    # Auto-set domain
    st.session_state.domain = "airbnb"

    st.markdown("""
<div style="text-align:center;padding:48px 0 32px">
  <div style="font-size:36px;font-weight:500;color:var(--color-text-primary);
  letter-spacing:-0.02em;margin-bottom:8px">
    🤖 Behind The Bot
  </div>
  <div style="font-size:16px;color:var(--color-text-tertiary)">
    See what happens between send and reply.
  </div>
</div>
""", unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:14px;padding:28px 24px;text-align:center;margin-bottom:24px">
  <div style="font-size:40px;margin-bottom:12px">🏠</div>
  <div style="font-size:18px;font-weight:500;color:var(--color-text-primary);margin-bottom:8px">
    Airbnb Customer Support Bot
  </div>
  <div style="font-size:13px;color:var(--color-text-tertiary);line-height:1.6;margin-bottom:20px">
    Cancellations · Refunds · Host disputes · Listing complaints
  </div>
  <div style="font-size:13px;color:var(--color-text-secondary);line-height:1.7;
  border-top:0.5px solid var(--color-border-tertiary);padding-top:16px;text-align:left">
    Ever wondered what actually happens when you message an AI chatbot?<br><br>
    Not the magic — the mechanics.<br><br>
    In the next 10 minutes you'll go behind the scenes of a real AI support system.
    Step by step. Layer by layer. Every decision visible.
  </div>
</div>
""", unsafe_allow_html=True)

        if st.button("Let's go →", type="primary", use_container_width=True):
            go_to("login")
