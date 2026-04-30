"""
RAG — Retrieval Augmented Generation Layer
───────────────────────────────────────────
Input  : user query + intent context + policy document(s)
Output : retrieved chunks with similarity scores, re-rank reasoning, warnings

Embeddings use your LLM provider's API — no torch or sentence-transformers needed.
OpenAI: text-embedding-3-small
Anthropic/Gemini: TF-IDF similarity (fast, no extra API cost)
"""

import time
import re
import math
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter
import numpy as np


@dataclass
class Chunk:
    id: int
    text: str
    tokens: int
    source: str
    section: str


@dataclass
class RetrievedChunk:
    chunk: Chunk
    similarity_score: float
    rerank_score: float
    final_rank: int
    retrieval_rank: int
    rank_changed: bool
    relevance_note: str


@dataclass
class RAGResult:
    query_used: str
    total_chunks: int
    retrieved_chunks: list
    context_text: str
    low_confidence_warning: bool
    warning_message: str
    chunk_size_used: int
    overlap_used: int
    top_k_used: int
    processing_time_ms: int
    all_chunk_scores: list
    embedding_method: str


def chunk_document(text: str, chunk_size: int = 400, overlap: int = 75) -> list:
    words = text.split()
    word_chunk_size = int(chunk_size / 1.3)
    word_overlap = int(overlap / 1.3)

    chunks = []
    start = 0
    chunk_id = 0
    current_section = "Introduction"

    section_patterns = [r'^SECTION \d+', r'^\d+\.\d+ [A-Z]', r'^━+']

    while start < len(words):
        end = min(start + word_chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        for line in chunk_text.split('\n'):
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    current_section = line.strip()[:60]
                    break

        token_estimate = int(len(chunk_words) * 1.3)
        chunks.append(Chunk(
            id=chunk_id,
            text=chunk_text,
            tokens=token_estimate,
            source="policy_document",
            section=current_section,
        ))
        chunk_id += 1
        start += word_chunk_size - word_overlap
        if end >= len(words):
            break

    return chunks


def _cosine_similarity(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Embedding methods ──────────────────────────────────────────────────────────

def _embed_openai(texts: list, llm_client) -> list:
    """Use OpenAI text-embedding-3-small — fast and cheap."""
    response = llm_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def _embed_tfidf(texts: list, query: str = None) -> list:
    """
    TF-IDF based similarity — no API cost, works for any provider.
    Returns sparse vectors over shared vocabulary.
    """
    all_texts = texts if query is None else [query] + texts

    # Build vocabulary
    def tokenize(t):
        return re.findall(r'\b[a-z]{2,}\b', t.lower())

    tokenized = [tokenize(t) for t in all_texts]
    vocab = sorted(set(w for doc in tokenized for w in doc))
    vocab_index = {w: i for i, w in enumerate(vocab)}

    # TF-IDF
    N = len(tokenized)
    df = Counter()
    for doc in tokenized:
        for w in set(doc):
            df[w] += 1

    def tfidf_vector(tokens):
        tf = Counter(tokens)
        vec = [0.0] * len(vocab)
        for w, count in tf.items():
            if w in vocab_index:
                tf_score = count / max(len(tokens), 1)
                idf_score = math.log((N + 1) / (df[w] + 1)) + 1
                vec[vocab_index[w]] = tf_score * idf_score
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    return [tfidf_vector(tok) for tok in tokenized]


def _get_embeddings(query: str, chunks: list, llm_client, provider: str):
    """Route to correct embedding method based on provider."""
    texts = [c.text for c in chunks]

    if provider == "openai":
        try:
            all_embeddings = _embed_openai([query] + texts, llm_client)
            return all_embeddings[0], all_embeddings[1:], "OpenAI text-embedding-3-small"
        except Exception:
            pass  # fall through to TF-IDF

    # TF-IDF for Anthropic, Gemini, or OpenAI fallback
    all_vecs = _embed_tfidf([query] + texts)
    return all_vecs[0], all_vecs[1:], "TF-IDF (no extra API cost)"


# ── Re-ranking ─────────────────────────────────────────────────────────────────

def _rerank_with_context(query, chunks, intent_context):
    intent = intent_context.get("primary_intent", "")
    urgency = intent_context.get("urgency", "medium")

    intent_keywords = {
        "cancellation_request": ["cancel", "cancellation", "policy tier", "flexible", "strict", "moderate"],
        "refund_request": ["refund", "reimburs", "money back", "payment", "processing"],
        "policy_question": ["section", "policy", "eligib", "qualify"],
        "complaint": ["inaccurac", "misrepresent", "dispute"],
    }
    urgency_keywords = {
        "high": ["within 24", "within 48", "day of", "last-minute"],
        "critical": ["24 hours", "same day", "emergency", "immediate"],
    }

    keywords = intent_keywords.get(intent, [])
    if urgency in urgency_keywords:
        keywords += urgency_keywords[urgency]

    for item in chunks:
        boost = 0.0
        text_lower = item.chunk.text.lower()
        keyword_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        boost += min(keyword_hits * 0.04, 0.15)
        item.rerank_score = min(item.similarity_score + boost, 1.0)
        item.relevance_note = (
            f"Context boost +{boost:.2f} ({keyword_hits} keyword matches)"
            if boost > 0.01 else "No context boost applied"
        )

    chunks.sort(key=lambda x: x.rerank_score, reverse=True)
    for i, item in enumerate(chunks):
        item.final_rank = i + 1
        item.rank_changed = item.final_rank != item.retrieval_rank

    return chunks


# ── Main retrieve function ─────────────────────────────────────────────────────

def retrieve(
    query: str,
    document_text: str,
    llm_client,
    provider: str,
    intent_context: dict,
    chunk_size: int = 400,
    overlap: int = 75,
    top_k: int = 3,
    min_similarity: float = 0.25,
    embed_model=None,   # kept for API compatibility, ignored
) -> RAGResult:
    start = time.time()

    chunks = chunk_document(document_text, chunk_size, overlap)
    query_emb, chunk_embs, embed_method = _get_embeddings(query, chunks, llm_client, provider)

    scored = []
    for chunk, emb in zip(chunks, chunk_embs):
        score = _cosine_similarity(query_emb, emb)
        scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    all_scores = [
        {
            "chunk_id": c.id,
            "section": c.section,
            "preview": c.text[:80] + "...",
            "similarity_score": round(s, 4),
            "rank": i + 1,
        }
        for i, (c, s) in enumerate(scored[:10])
    ]

    top_candidates = scored[:max(top_k * 2, 6)]
    retrieved = [
        RetrievedChunk(
            chunk=c,
            similarity_score=round(s, 4),
            rerank_score=round(s, 4),
            final_rank=0,
            retrieval_rank=i + 1,
            rank_changed=False,
            relevance_note="",
        )
        for i, (c, s) in enumerate(top_candidates)
    ]

    reranked = _rerank_with_context(query, retrieved, intent_context)
    final = reranked[:top_k]

    context_parts = [
        f"[Policy Chunk {i+1} | Score: {item.rerank_score:.2f}]\n{item.chunk.text}"
        for i, item in enumerate(final)
    ]
    context_text = "\n\n---\n\n".join(context_parts)

    best_score = final[0].rerank_score if final else 0.0
    low_confidence = best_score < min_similarity
    warning = ""
    if low_confidence:
        warning = (
            f"⚠️ Best retrieval score is {best_score:.2f} (threshold: {min_similarity}). "
            "The retrieved chunks may not be relevant to this query. "
            "Consider improving the knowledge base or rephrasing the query."
        )

    processing_time = int((time.time() - start) * 1000)

    return RAGResult(
        query_used=query,
        total_chunks=len(chunks),
        retrieved_chunks=final,
        context_text=context_text,
        low_confidence_warning=low_confidence,
        warning_message=warning,
        chunk_size_used=chunk_size,
        overlap_used=overlap,
        top_k_used=top_k,
        processing_time_ms=processing_time,
        all_chunk_scores=all_scores,
        embedding_method=embed_method,
    )
