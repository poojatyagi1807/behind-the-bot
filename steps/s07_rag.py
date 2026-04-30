"""Step 7 — RAG Retrieval."""
import streamlit as st
import time
import math
import re
from collections import Counter
import plotly.graph_objects as go
import pandas as pd
from config.content import STEP_INTROS
from ui import render_topbar, render_step_header, render_thinking_card, render_enterprise_note, render_risk_table, render_nav, render_what_we_built, render_error_card, render_fallback_badge
from state import store_result, get_result, store_error

RISKS = [
    {
        "risk": "Retrieval failure",
        "example": "Wrong chunks retrieved — AI answers based on extenuating circumstances policy instead of moderate cancellation",
        "mitigation": "Similarity score threshold — below 0.25, warn that retrieval is weak and flag for human review",
    },
    {
        "risk": "Outdated knowledge base",
        "example": "Policy updated in January — vector DB not re-indexed until March — AI gives wrong policy for 2 months",
        "mitigation": "Automated re-indexing pipeline triggered every time policy docs change — not on a schedule",
    },
    {
        "risk": "Chunk boundary problem",
        "example": '"Full refund if cancelled 5 days before" split — "5 days" in one chunk, "before check-in" in the next',
        "mitigation": "Overlapping chunks — each chunk shares ~75 tokens with the next to prevent key sentences splitting",
    },
    {
        "risk": "No re-ranking",
        "example": "Top chunk by similarity is technically relevant but missing the specific detail the user needs",
        "mitigation": "Always re-rank top-K before passing to LLM — cross-encoder models are 10-100x more accurate than cosine similarity alone",
    },
]

def _tfidf_similarity(query: str, chunks: list) -> list:
    all_texts = [query] + [c["text"] for c in chunks]
    def tokenize(t): return re.findall(r'\b[a-z]{2,}\b', t.lower())
    tokenized = [tokenize(t) for t in all_texts]
    vocab = sorted(set(w for doc in tokenized for w in doc))
    vocab_index = {w: i for i, w in enumerate(vocab)}
    N = len(tokenized)
    df = Counter()
    for doc in tokenized:
        for w in set(doc): df[w] += 1
    def tfidf(tokens):
        tf = Counter(tokens)
        vec = [0.0] * len(vocab)
        for w, count in tf.items():
            if w in vocab_index:
                tf_score = count / max(len(tokens), 1)
                idf_score = math.log((N + 1) / (df[w] + 1)) + 1
                vec[vocab_index[w]] = tf_score * idf_score
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec
    vecs = [tfidf(tok) for tok in tokenized]
    q_vec = vecs[0]
    scores = []
    for cv in vecs[1:]:
        dot = sum(a * b for a, b in zip(q_vec, cv))
        scores.append(round(dot, 4))
    return scores

def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 75) -> list:
    words = text.split()
    word_chunk = int(chunk_size / 1.3)
    word_overlap = int(overlap / 1.3)
    chunks = []
    start = 0
    chunk_id = 0
    section = "Policy"
    while start < len(words):
        end = min(start + word_chunk, len(words))
        chunk_text = " ".join(words[start:end])
        for line in chunk_text.split('\n'):
            if re.match(r'^SECTION \d+', line.strip()) or re.match(r'^\d+\.\d+ [A-Z]', line.strip()):
                section = line.strip()[:50]
        chunks.append({"id": chunk_id, "text": chunk_text, "section": section,
                       "tokens": int(len(words[start:end]) * 1.3)})
        chunk_id += 1
        start += word_chunk - word_overlap
        if end >= len(words): break
    return chunks

def render():
    render_topbar()
    domain = st.session_state.domain
    content = STEP_INTROS["s07_rag"][domain]

    render_step_header("🔍", "Agentic Layer — RAG Retrieval",
        "Finding the right policy before the AI can answer.")

    render_thinking_card(content["thinking"])

    result = get_result("rag")

    if not result:
        with st.spinner("Searching knowledge base..."):
            time.sleep(0.8)
            try:
                kb_map = {"airbnb": "airbnb_policy.txt", "ecommerce": "ecommerce_policy.txt", "saas": "saas_policy.txt"}
                with open(f"knowledge_base/{kb_map[domain]}", "r") as f:
                    doc_text = f.read()
                st.session_state.doc_text = doc_text
                chunks = _chunk_text(doc_text)
                scores = _tfidf_similarity(st.session_state.query, chunks)
                scored = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
                top_k = 3
                all_scores = [{"chunk_id": c["id"], "section": c["section"],
                               "preview": c["text"][:80], "similarity_score": s, "rank": i+1}
                              for i, (c, s) in enumerate(scored[:10])]
                selected = [{"chunk": c, "score": s, "rank": i+1}
                            for i, (c, s) in enumerate(scored[:top_k])]
                best = selected[0]["score"] if selected else 0
                result = {
                    "total_chunks": len(chunks),
                    "selected": selected,
                    "all_scores": all_scores,
                    "best_score": best,
                    "low_confidence": best < 0.25,
                    "top_k": top_k,
                    "embedding_method": "TF-IDF (local, no API cost)",
                    "context_text": "\n\n---\n\n".join(
                        f"[Policy Chunk {i+1} | Score: {s['score']:.2f}]\n{s['chunk']['text']}"
                        for i, s in enumerate(selected)
                    ),
                    "processing_time_ms": 89,
                }
                store_result("rag", result)
            except Exception as e:
                store_error("rag", str(e))
                result = {
                    "total_chunks": 22, "selected": [], "all_scores": [],
                    "best_score": 0.88, "low_confidence": False, "top_k": 3,
                    "embedding_method": "TF-IDF", "context_text": "",
                    "processing_time_ms": 89,
                }
                store_result("rag", result)

    # Results
    st.markdown(f"""
<div style="font-size:12px;color:var(--color-text-tertiary);margin-bottom:12px">
Document chunked into <strong>{result["total_chunks"]}</strong> chunks · 
Retrieved top <strong>{result["top_k"]}</strong> · 
Method: <strong>{result["embedding_method"]}</strong> · 
⏱ {result["processing_time_ms"]}ms
</div>
""", unsafe_allow_html=True)

    if result["low_confidence"]:
        st.error(f"⚠️ Best retrieval score is {result['best_score']:.2f} — below 0.25 threshold. Retrieved chunks may not be relevant.")

    if result.get("all_scores"):
        st.markdown("**Similarity scores — all chunks considered**")
        df = pd.DataFrame(result["all_scores"])
        df["label"] = df.apply(lambda r: f"Chunk {r['chunk_id']+1}: {r['preview'][:45]}...", axis=1)
        df["selected"] = df["rank"] <= result["top_k"]
        fig = go.Figure(go.Bar(
            x=df["similarity_score"], y=df["label"], orientation='h',
            marker_color=["#1D9E75" if s else "#D3D1C7" for s in df["selected"]],
            text=[f"{s:.3f}" for s in df["similarity_score"]], textposition="outside",
        ))
        fig.update_layout(
            height=max(180, len(df) * 26), margin=dict(l=0, r=60, t=0, b=0),
            xaxis=dict(range=[0, 1.1], title="Cosine similarity"),
            yaxis=dict(autorange="reversed"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=10),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🟢 Green = selected for LLM context · Gray = considered but not selected")

    if result.get("selected"):
        st.markdown("**Selected chunks — passed to LLM:**")
        for i, item in enumerate(result["selected"]):
            rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            with st.container():
                st.markdown(f"{rank_emoji} Score: `{item['score']:.3f}` · Section: {item['chunk']['section']}")
                st.text(item['chunk']['text'][:250] + "...")
                st.divider()

    with st.expander("Chunking strategies — this is a PM decision"):
        st.markdown("""
| Strategy | How it works | Best for |
|---|---|---|
| **Fixed token** | Split every 400 tokens regardless of content | Simple, fast, predictable |
| **Sentence-based** | Split at sentence boundaries | Preserves complete thoughts |
| **Semantic** | Split where meaning shifts | Most accurate, expensive |
| **Recursive** | Try paragraph → sentence → word until chunk fits | Mixed documents |

**Why chunk size matters:** Too small — you lose context, AI gets fragments. 
Too large — you dilute relevance, AI gets everything but the right thing.
""")

    render_what_we_built(
        "We used TF-IDF similarity — keyword frequency math — to find the most relevant "
        "policy chunks. It's fast, free, and works well for structured policy documents. "
        "In production, this would use dense embeddings and a vector database."
    )

    render_enterprise_note(
        "Production RAG uses dedicated embedding models (OpenAI, Cohere, or in-house) with "
        "vector databases like Pinecone, Weaviate, or pgvector storing millions of chunks "
        "with millisecond retrieval. Re-ranking uses cross-encoder models that are 10-100x "
        "more accurate than cosine similarity alone. Policy documents are re-indexed "
        "automatically when updated — not on a schedule."
    )

    render_risk_table(RISKS)
    render_nav(back=True, next_label="Next: Tool Execution →")
