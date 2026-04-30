"""
Shared UI components used across all step files.
"""

import streamlit as st
from state import go_next, go_back, progress_pct, current_step_index, STEPS


def render_topbar():
    """Top navigation bar with progress."""
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
padding:8px 0 16px;border-bottom:0.5px solid var(--color-border-tertiary);margin-bottom:20px">
  <div style="font-size:15px;font-weight:500;color:var(--color-text-primary)">
    🤖 Behind The Bot
  </div>
  <div style="font-size:12px;color:var(--color-text-tertiary)">
    Step {current_step_index() + 1} of {len(STEPS)}
  </div>
</div>
<div style="height:3px;background:var(--color-border-tertiary);border-radius:2px;margin-bottom:24px">
  <div style="height:3px;width:{progress_pct()*100:.0f}%;background:#378ADD;border-radius:2px;transition:width 0.3s"></div>
</div>
""", unsafe_allow_html=True)


def render_step_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"""
<div style="margin-bottom:16px">
  <div style="font-size:22px;font-weight:500;color:var(--color-text-primary)">{icon} {title}</div>
  {"<div style='font-size:13px;color:var(--color-text-tertiary);margin-top:4px'>" + subtitle + "</div>" if subtitle else ""}
</div>
""", unsafe_allow_html=True)


def render_thinking_card(text: str):
    """The 'what the AI is thinking' intro card — appears instantly."""
    st.markdown(f"""
<div style="background:var(--color-background-secondary);border-left:3px solid #378ADD;
border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:16px;
font-size:13px;color:var(--color-text-secondary);line-height:1.6;font-style:italic">
{text}
</div>
""", unsafe_allow_html=True)


def render_enterprise_note(text: str):
    """Blue enterprise callout box."""
    st.markdown(f"""
<div style="background:#EBF4FD;border:0.5px solid #B5D4F4;border-radius:8px;
padding:12px 14px;margin:12px 0;font-size:12px;color:#0C447C;line-height:1.6">
🏢 <strong>At enterprise scale</strong> — {text}
</div>
""", unsafe_allow_html=True)


def render_error_card(step_name: str, error: str, show_retry: bool = True):
    """Error card — never shows raw traceback."""
    st.markdown(f"""
<div style="background:#FCEBEB;border:0.5px solid #F7C1C1;border-radius:8px;
padding:12px 14px;margin:12px 0;font-size:12px;color:#501313;line-height:1.6">
⚠️ <strong>This step hit a snag</strong> — {error}
<br><br>The result below uses a pre-computed example so you can keep going.
</div>
""", unsafe_allow_html=True)


def render_fallback_badge():
    st.markdown("""
<div style="display:inline-block;background:#FAEEDA;border:0.5px solid #FAC775;
border-radius:4px;padding:2px 8px;font-size:10px;color:#633806;margin-bottom:8px">
⚠️ Pre-computed example — API call failed
</div>
""", unsafe_allow_html=True)


def render_nav(back: bool = True, next_label: str = "Next step →", next_disabled: bool = False):
    """Bottom navigation — back and next buttons."""
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    cols = st.columns([1, 3, 1])
    with cols[0]:
        if back and current_step_index() > 0:
            if st.button("← Back", use_container_width=True):
                go_back()
    with cols[2]:
        if st.button(next_label, type="primary", use_container_width=True, disabled=next_disabled):
            go_next()


def render_risk_table(risks: list):
    """
    Render the risk table with 3 columns: Risk, Example, Mitigation.
    risks = list of dicts with keys: risk, example, mitigation
    """
    st.markdown("**⚠️ What can go wrong**")
    header = "| Risk | Example | Mitigation |\n|---|---|---|\n"
    rows = "\n".join(
        f"| **{r['risk']}** | {r['example']} | {r['mitigation']} |"
        for r in risks
    )
    st.markdown(header + rows)


def render_what_we_built(text: str):
    st.markdown(f"""
<div style="font-size:12px;color:var(--color-text-secondary);
background:var(--color-background-secondary);border-radius:8px;
padding:10px 14px;margin:8px 0;line-height:1.6">
<strong style="color:var(--color-text-primary)">What we built (simplified)</strong><br>{text}
</div>
""", unsafe_allow_html=True)


def render_key_prompt():
    """Shown after free run is used — prompt for personal Gemini key."""
    st.markdown("---")
    st.markdown("### You just saw the full pipeline — for free 🎉")
    st.markdown("""
You used our Gemini API credit for that run. To keep exploring — try different queries, 
test edge cases, or run the batch test — add your own free Gemini key.

**It takes 2 minutes and costs nothing:**
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key**
3. Paste it below
""")
    key = st.text_input("Your Gemini API key", type="password", placeholder="AIza...")
    if key:
        st.session_state.api_key = key
        st.session_state.llm_client = None
        st.success("Key saved — you're all set to keep exploring.")
        st.rerun()
