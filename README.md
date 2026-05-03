# 🤖 Behind The Bot

> **See what happens between send and reply.**

🔗 **Try it live:** *Coming soon on Streamlit Cloud*

Most people experience AI as a black box — you type something, magic happens, an answer appears. Behind The Bot opens that box. Step by step. Layer by layer. Every decision visible.

Built for students, curious professionals, and product managers who want to understand how AI customer support actually works — not the theory, the mechanics.

---

## What it is

Behind The Bot walks you through a simulated Airbnb customer support pipeline. You play a guest with a real booking problem. The app shows you exactly what happens at every layer between your message and the response — live, as it runs.

**13 steps. Every layer exposed:**

| Step | What you see |
|---|---|
| 🔐 Authentication | Your session profile, trust score, risk scoring, bot detection |
| 💬 Your query | Pick a scenario or type your own |
| 🛡️ Input guardrails | LlamaGuard content check, Presidio PII detection, prompt injection scan |
| 🎯 Intent classification | Two-stage ML cascade — fast classifier first, LLM only if needed |
| 🤖 Agentic layer intro | What ReAct means, how MCP servers work, tools available |
| 🔍 RAG retrieval | Every chunk's similarity score, re-ranking logic, what made the cut |
| 🔧 Tool execution | Simulated API calls with real inputs and outputs |
| 🧠 LLM reasoning | Full context window, chain of thought, draft response |
| 🔒 Output guardrails | Five checks — PII, hallucination, policy compliance, escalation, tone |
| 💬 Final response | What the user actually sees |
| 🧑‍⚖️ LLM-as-judge | A second AI evaluates the pipeline and tells you what went wrong and why |
| 📊 Observability | Full conversation trace, what it feeds into, system architecture |

Each step explains:
- **What we built** (simplified version)
- **What enterprises actually use** (production scale detail)
- **What can go wrong** (with specific examples and mitigations)
- **Real snapshots** from LlamaGuard, Presidio, LangSmith, MCP protocol

---

## Who it's for

**Students** learning how AI systems work — not just conceptually but mechanically. Every layer is visible. Every decision is explained.

**Product managers** who need to understand what they're building before they build it. Walk through the pipeline once and you'll know what questions to ask your engineering team.

**Anyone** who's ever wondered why AI chatbots sometimes get things right, sometimes get things wrong, and what's actually happening in between.

---

## Quick start

### Prerequisites
- Python 3.10 or higher
- A free Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### Run locally

```bash
# Clone the repo
git clone https://github.com/poojatyagi1807/behind-the-bot.git
cd behind-the-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "your-key-here"' > .streamlit/secrets.toml

# Run
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Get a free Gemini API key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key**
3. Create a new key — it's free, no credit card required
4. Paste it into `.streamlit/secrets.toml`

---

## What you'll experience

You arrive as one of 10 pre-built guest profiles — each with a different trust score, booking history, and account age. The profile you get changes how the pipeline treats your request. A guest with 87/100 trust and zero disputes gets a different experience than one with 28/100 trust and 9 refund requests. That's intentional.

You pick a query — or type your own. The pipeline runs live. Each layer appears on screen the moment it completes. You don't wait for everything to finish — you read the intent classification results while the tools are still fetching data.

At the intent classification step you'll see the two-stage cascade in action — a fast scikit-learn ML classifier runs first in under 5ms. Only if it's not confident enough does it invoke Gemini. You can watch which path your query takes.

At the end, an LLM-as-judge evaluates the entire pipeline and tells you what went well, which layer was the weakest link, and what a product manager should do about it. Sometimes it catches things you didn't notice — like chain of thought leaking into the final response.

---

## File structure

```
behind-the-bot/
├── app.py                     # Entry point — step router
├── state.py                   # Session state and flow management
├── ui.py                      # Shared UI components
├── requirements.txt
├── config/
│   ├── profiles.py            # 10 user profiles covering all trust scenarios
│   ├── content.py             # Domain-specific intro content per step
│   └── defaults.py            # RAG settings, system prompts, guardrail configs
├── knowledge_base/
│   └── airbnb_policy.txt      # Airbnb-style cancellation and refund policy
├── layers/
│   ├── ml_classifier.py       # Scikit-learn TF-IDF + LR — Stage 1 of cascade
│   ├── intent_classifier.py   # Two-stage cascade orchestrator
│   ├── rag.py                 # TF-IDF chunking, embedding, retrieval, re-ranking
│   ├── tools.py               # Simulated tool execution
│   ├── llm_reasoning.py       # Context assembly and LLM call
│   └── guardrails.py          # Output validation checks
└── steps/
    ├── s01_landing.py         # Landing screen
    ├── s02_login.py           # Profile assignment and authentication
    ├── s03_query.py           # Query input
    ├── s04_input_guardrails.py
    ├── s05_intent.py          # Two-stage ML + LLM cascade visualization
    ├── s06_agentic_intro.py
    ├── s07_rag.py
    ├── s08_tools.py
    ├── s09_reasoning.py
    ├── s10_output_guardrails.py
    ├── s11_response.py
    ├── s11b_judge.py          # LLM-as-judge evaluation
    └── s12_observability.py
```

---

## Technical notes

**Two-stage intent cascade** — A scikit-learn TF-IDF + Logistic Regression classifier trained on 120 labeled examples runs first. Confidence above 75% means no LLM call needed. Below 75% invokes Gemini for nuanced classification. This mirrors how production systems work — fast ML for the majority, expensive LLM only for edge cases.

**Embeddings** — TF-IDF similarity for RAG retrieval. No PyTorch, no sentence-transformers. Keeps dependencies minimal and works well for structured policy documents. In production you'd use dense embeddings via OpenAI, Cohere, or a dedicated model.

**LLM** — Gemini 2.0 Flash via Google's API. Free tier supported. The app makes approximately 3-5 API calls per complete pipeline run depending on whether the ML classifier triggers the LLM.

**No data stored** — Your API key lives in session memory only and is gone when you close the browser tab. No database, no user accounts, no logging.

**Error handling** — Every API-dependent step has a pre-computed fallback. If an API call fails, the pipeline continues with a realistic example result rather than crashing.

---

## The 10 profiles

Each profile tells a different story and changes how the pipeline behaves:

| Profile | Trust | Story |
|---|---|---|
| Sarah M. | 87/100 | Trusted veteran — smooth path |
| Alex K. | 34/100 | Brand new user — system is cautious |
| Marcus T. | 28/100 | 3 years but 9 refund requests — guardrails tighten |
| Priya R. | 94/100 | Power user — fastest path, auto-approve |
| Jamie L. | 51/100 | Unverified — verification prompt triggered |
| User 9823 | 12/100 | New account + VPN — maximum scrutiny |
| Chen W. | 62/100 | Reformed history — recovering score |
| David S. | 78/100 | Corporate account — different routing |
| Maria G. | 71/100 | Emotional situation — empathy mode |
| Robert F. | 58/100 | Long-inactive + new device — re-verification |

---

## Built with

- [Streamlit](https://streamlit.io) — UI framework
- [Google Gemini](https://aistudio.google.com) — LLM for reasoning and LLM-as-judge
- [Scikit-learn](https://scikit-learn.org) — ML intent classifier (Stage 1 of cascade)
- [Plotly](https://plotly.com) — RAG similarity score visualisations
- Python standard library — TF-IDF embeddings for RAG, no external ML dependencies

---

## About

Built by [Pooja Tyagi](https://linkedin.com/in/poojatyagi) — Senior Product Manager with a background in AI/ML platform products.

Behind The Bot started as a learning tool for understanding AI pipelines and grew into something more — a way to make the invisible visible for anyone trying to understand how modern AI support systems actually work.

---

*If this was useful, share it with someone trying to understand AI systems. That's the whole point.*

---

## What it is

Behind The Bot walks you through a simulated Airbnb customer support pipeline. You play a guest with a real booking problem. The app shows you exactly what happens at every layer between your message and the response — live, as it runs.

**12 steps. Every layer exposed:**

| Step | What you see |
|---|---|
| 🔐 Authentication | Your session profile, trust score, risk scoring, bot detection |
| 💬 Your query | Pick a scenario or type your own |
| 🛡️ Input guardrails | LlamaGuard content check, Presidio PII detection, prompt injection scan |
| 🎯 Intent classification | Primary + secondary intents, confidence scores, sentiment, urgency, routing decision |
| 🤖 Agentic layer intro | What ReAct means, how MCP servers work, tools available |
| 🔍 RAG retrieval | Every chunk's similarity score, re-ranking logic, what made the cut |
| 🔧 Tool execution | Simulated API calls with real inputs and outputs |
| 🧠 LLM reasoning | Full context window, chain of thought, draft response |
| 🔒 Output guardrails | Five checks — PII, hallucination, policy compliance, escalation, tone |
| 💬 Final response | What the user actually sees |
| 🧑‍⚖️ LLM-as-judge | A second AI evaluates the pipeline and tells you what went wrong and why |
| 📊 Observability | Full conversation trace, what it feeds into, system architecture |

Each step explains:
- **What we built** (simplified version)
- **What enterprises actually use** (production scale detail)
- **What can go wrong** (with specific examples and mitigations)
- **Real snapshots** from LlamaGuard, Presidio, LangSmith, MCP protocol

---

## Who it's for

**Students** learning how AI systems work — not just conceptually but mechanically. Every layer is visible. Every decision is explained.

**Product managers** who need to understand what they're building before they build it. Walk through the pipeline once and you'll know what questions to ask your engineering team.

**Anyone** who's ever wondered why AI chatbots sometimes get things right, sometimes get things wrong, and what's actually happening in between.

---

## Quick start

### Prerequisites
- Python 3.10 or higher
- A free Gemini API key from [aistudio.google.com](https://aistudio.google.com)

### Run locally

```bash
# Clone the repo
git clone https://github.com/poojatyagi1807/behind-the-bot.git
cd behind-the-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key
mkdir -p .streamlit
echo 'GEMINI_API_KEY = "your-key-here"' > .streamlit/secrets.toml

# Run
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Get a free Gemini API key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key**
3. Create a new key — it's free, no credit card required
4. Paste it into `.streamlit/secrets.toml`

---

## What you'll experience

You arrive as one of 10 pre-built guest profiles — each with a different trust score, booking history, and account age. The profile you get changes how the pipeline treats your request. A guest with 87/100 trust and zero disputes gets a different experience than one with 28/100 trust and 9 refund requests. That's intentional.

You pick a query — or type your own. The pipeline runs live. Each layer appears on screen the moment it completes. You don't wait for everything to finish — you read the intent classification results while the tools are still fetching data.

At the end, an LLM-as-judge evaluates the entire pipeline and tells you what went well, which layer was the weakest link, and what a product manager should do about it.

---

## File structure

```
behind-the-bot/
├── app.py                     # Entry point — step router
├── state.py                   # Session state and flow management
├── ui.py                      # Shared UI components
├── requirements.txt
├── config/
│   ├── profiles.py            # 10 user profiles covering all trust scenarios
│   ├── content.py             # Domain-specific intro content per step
│   └── defaults.py            # RAG settings, system prompts, guardrail configs
├── knowledge_base/
│   └── airbnb_policy.txt      # Airbnb-style cancellation and refund policy
├── layers/
│   ├── intent_classifier.py   # LLM-based intent classification
│   ├── rag.py                 # TF-IDF chunking, embedding, retrieval, re-ranking
│   ├── tools.py               # Simulated tool execution
│   ├── llm_reasoning.py       # Context assembly and LLM call
│   └── guardrails.py          # Output validation checks
└── steps/
    ├── s01_landing.py         # Landing screen
    ├── s02_login.py           # Profile assignment and authentication
    ├── s03_query.py           # Query input
    ├── s04_input_guardrails.py
    ├── s05_intent.py
    ├── s06_agentic_intro.py
    ├── s07_rag.py
    ├── s08_tools.py
    ├── s09_reasoning.py
    ├── s10_output_guardrails.py
    ├── s11_response.py
    ├── s11b_judge.py          # LLM-as-judge evaluation
    └── s12_observability.py
```

---

## Technical notes

**Embeddings** — We use TF-IDF similarity for RAG retrieval. No PyTorch, no sentence-transformers. This keeps the dependency footprint small and works well for structured policy documents. In production you'd use dense embeddings via OpenAI, Cohere, or a dedicated model.

**LLM** — Gemini 2.0 Flash via Google's API. Free tier supported. The app makes approximately 4-6 API calls per complete pipeline run.

**No data stored** — Your API key lives in session memory only and is gone when you close the browser tab. No database, no user accounts, no logging.

**Error handling** — Every API-dependent step has a pre-computed fallback. If an API call fails, the pipeline continues with a realistic example result rather than crashing.

---

## The 10 profiles

Each profile tells a different story and changes how the pipeline behaves:

| Profile | Trust | Story |
|---|---|---|
| Sarah M. | 87/100 | Trusted veteran — smooth path |
| Alex K. | 34/100 | Brand new user — system is cautious |
| Marcus T. | 28/100 | 3 years but 9 refund requests — guardrails tighten |
| Priya R. | 94/100 | Power user — fastest path, auto-approve |
| Jamie L. | 51/100 | Unverified — verification prompt triggered |
| User 9823 | 12/100 | New account + VPN — maximum scrutiny |
| Chen W. | 62/100 | Reformed history — recovering score |
| David S. | 78/100 | Corporate account — different routing |
| Maria G. | 71/100 | Emotional situation — empathy mode |
| Robert F. | 58/100 | Long-inactive + new device — re-verification |

---

## Built with

- [Streamlit](https://streamlit.io) — UI framework
- [Google Gemini](https://aistudio.google.com) — LLM for intent classification, reasoning, and LLM-as-judge
- [Plotly](https://plotly.com) — RAG similarity score visualisations
- Python standard library — TF-IDF embeddings, no external ML dependencies

---

## About

Built by [Pooja Tyagi](https://linkedin.com/in/poojatyagi) — Senior Product Manager with a background in AI/ML platform products.

Behind The Bot started as a learning tool for understanding AI pipelines and grew into something more — a way to make the invisible visible for anyone trying to understand how modern AI support systems actually work.

---

*If this was useful, share it with someone trying to understand AI systems. That's the whole point.*
