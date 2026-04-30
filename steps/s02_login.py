"""Step 2 — Login: assign random profile, explain authentication."""
import streamlit as st
import time
from config.profiles import get_random_profile
from ui import render_topbar, render_step_header, render_enterprise_note, render_risk_table, render_nav, render_what_we_built

def render():
    render_topbar()
    render_step_header("🔐", "First things first — let's get you logged in",
        "Just like a real support chatbot, the AI needs to know who you are before it can help.")

    # Assign profile if not done
    if not st.session_state.profile:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
<div style="text-align:center;padding:20px;background:var(--color-background-secondary);
border-radius:12px;border:0.5px solid var(--color-border-tertiary)">
  <div style="font-size:13px;color:var(--color-text-secondary);margin-bottom:16px">
    We've pre-filled a random guest account for you.<br>Just hit Login.
  </div>
""", unsafe_allow_html=True)
            username = st.text_input("Username", value="guest_7829", disabled=True)
            password = st.text_input("Password", value="••••••••", type="password", disabled=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("Login →", type="primary", use_container_width=True):
                with st.spinner("Fetching your profile..."):
                    time.sleep(1.2)
                profile = get_random_profile()
                st.session_state.profile = profile
                st.rerun()
        return

    # Profile loaded — show it
    p = st.session_state.profile
    trust_color = "#1D9E75" if p["trust_score"] >= 70 else "#BA7517" if p["trust_score"] >= 40 else "#E24B4A"
    trust_label = "High" if p["trust_score"] >= 70 else "Medium" if p["trust_score"] >= 40 else "Low"

    st.success(f"✅ Welcome back, {p['name']}!")

    # Profile card
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:16px">
  <div style="font-size:12px;font-weight:500;color:var(--color-text-tertiary);
  letter-spacing:0.05em;margin-bottom:12px">YOUR SESSION PROFILE</div>
  <table style="width:100%;font-size:12px;border-collapse:collapse">
    <tr><td style="color:var(--color-text-tertiary);padding:4px 0">Member since</td>
        <td style="color:var(--color-text-primary);font-weight:500;text-align:right">{p["member_since"]}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:4px 0">Total bookings</td>
        <td style="color:var(--color-text-primary);font-weight:500;text-align:right">{p["bookings"]}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:4px 0">Past disputes</td>
        <td style="color:var(--color-text-primary);font-weight:500;text-align:right">{p["past_disputes"]}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:4px 0">Refund requests</td>
        <td style="color:var(--color-text-primary);font-weight:500;text-align:right">{p["refund_requests"]}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:4px 0">Account status</td>
        <td style="color:var(--color-text-primary);font-weight:500;text-align:right">{p["account_status"]}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:4px 0">Device</td>
        <td style="color:var(--color-text-primary);font-weight:500;text-align:right">{p["device"]}</td></tr>
    <tr><td style="color:var(--color-text-tertiary);padding:4px 0">Trust score</td>
        <td style="font-weight:500;text-align:right;color:{trust_color}">{p["trust_score"]} / 100 — {trust_label}</td></tr>
  </table>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
<div style="background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);
border-radius:10px;padding:16px;height:100%">
  <div style="font-size:12px;font-weight:500;color:var(--color-text-tertiary);
  letter-spacing:0.05em;margin-bottom:12px">PIPELINE IMPACT</div>
  <div style="font-size:12px;color:var(--color-text-secondary);line-height:1.7">
    {p["pipeline_note"]}
  </div>
  <div style="margin-top:12px;font-size:11px;color:var(--color-text-tertiary);font-style:italic">
    {p["story"]}
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    render_what_we_built(
        "In a real support chat, your account profile is fetched the moment you log in — "
        "booking history, trust score, past disputes, all of it. We've simulated that here "
        "with a pre-built profile so you can see exactly what the AI sees about you before "
        "you've typed a single word."
    )

    st.markdown("**🔐 Three things ran in parallel while you logged in**")

    st.markdown("""
| | What it did | If it fails | Mitigation |
|---|---|---|---|
| **Identity check** | Matched session token to your account — like a concert wristband | Stolen token = attacker impersonates you (2022 Uber breach) | Re-verify identity for high-stakes actions — large refunds, account changes — even with valid token |
| **Risk scoring** | ML model scored you based on 150+ signals — history, payments, disputes | New users unfairly penalized — same question, worse experience | Separate new user pathway — don't apply fraud-trained model to first-time users without calibration |
| **Bot detection** | Checked you're human — typing speed, request patterns, device behavior | Accessibility tools flagged as bots before AI sees message | Allowlist known accessibility tools + offer CAPTCHA fallback before hard blocking |
""")

    render_enterprise_note(
        "Airbnb's trust and safety team maintains a separate ML model just for risk scoring — "
        "it runs before any support AI sees your message. It considers 150+ signals including "
        "booking patterns, payment history, and device reputation. A trusted member asking for "
        "a refund gets good faith. A new account gets more scrutiny. Same AI, different context."
    )

    if st.button("↩ Try a different profile", use_container_width=False):
        st.session_state.profile = None
        st.rerun()

    render_nav(back=True, next_label="Ask your question →")
