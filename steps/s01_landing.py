"""Step 1 — Landing: pick your domain."""
import streamlit as st
from state import go_to

def render():
    st.markdown("""
<div style="text-align:center;padding:40px 0 24px">
  <div style="font-size:32px;font-weight:500;color:var(--color-text-primary);letter-spacing:-0.02em">
    🤖 Behind The Bot
  </div>
  <div style="font-size:16px;color:var(--color-text-tertiary);margin-top:8px">
    See what happens between send and reply.
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="max-width:560px;margin:0 auto 32px;text-align:center;
font-size:14px;color:var(--color-text-secondary);line-height:1.7">
Ever wondered what actually happens when you message an AI chatbot?<br>
Not the magic — the mechanics.<br><br>
In the next 10 minutes, you'll go behind the scenes of a real AI customer 
support system. Step by step. Layer by layer.
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='text-align:center;font-size:13px;font-weight:500;color:var(--color-text-tertiary);margin-bottom:16px'>Pick your world</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    domains = [
        ("airbnb", "🏠", "Airbnb", "Cancellations · Refunds · Host disputes", col1),
        ("ecommerce", "🛒", "E-commerce", "Returns · Damaged items · Missing orders", col2),
        ("saas", "💻", "SaaS", "Subscriptions · Billing · Account issues", col3),
    ]

    for domain_id, icon, name, desc, col in domains:
        with col:
            selected = st.session_state.get("domain") == domain_id
            border = "#378ADD" if selected else "var(--color-border-tertiary)"
            bg = "#EBF4FD" if selected else "var(--color-background-secondary)"

            st.markdown(f"""
<div style="border:1.5px solid {border};background:{bg};border-radius:12px;
padding:20px 16px;text-align:center;margin-bottom:8px">
  <div style="font-size:28px">{icon}</div>
  <div style="font-size:14px;font-weight:500;color:var(--color-text-primary);margin:8px 0 4px">{name}</div>
  <div style="font-size:11px;color:var(--color-text-tertiary);line-height:1.5">{desc}</div>
</div>
""", unsafe_allow_html=True)
            if st.button(f"Choose {name}", key=f"domain_{domain_id}", use_container_width=True):
                st.session_state.domain = domain_id
                st.rerun()

    if st.session_state.get("domain"):
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        col_c = st.columns([1, 2, 1])[1]
        with col_c:
            if st.button("Let's go →", type="primary", use_container_width=True):
                go_to("login")
