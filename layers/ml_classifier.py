"""
ML Intent Classifier — Stage 1 of the cascade
──────────────────────────────────────────────
TF-IDF + Logistic Regression trained on labeled examples.
Runs in <5ms. No GPU, no torch, no downloads.

If confidence > 0.75 → return result, skip LLM
If confidence <= 0.75 → pass to LLM classifier
"""

import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import numpy as np

# ── Training data ─────────────────────────────────────────────────────────────
# ~15 examples per intent — enough for a reliable fast classifier
TRAINING_DATA = [
    # cancellation_request
    ("I want to cancel my reservation", "cancellation_request"),
    ("I need to cancel my booking", "cancellation_request"),
    ("Please cancel my trip", "cancellation_request"),
    ("I'd like to cancel my stay", "cancellation_request"),
    ("Can I cancel my reservation?", "cancellation_request"),
    ("I want to call off my booking", "cancellation_request"),
    ("Cancel my reservation please", "cancellation_request"),
    ("I need to call off my trip", "cancellation_request"),
    ("How do I cancel?", "cancellation_request"),
    ("I want to cancel and get money back", "cancellation_request"),
    ("Please cancel booking BK-29471", "cancellation_request"),
    ("I changed my mind and want to cancel", "cancellation_request"),
    ("Cancel everything", "cancellation_request"),
    ("I no longer need the reservation", "cancellation_request"),
    ("I want to cancel my upcoming stay", "cancellation_request"),

    # refund_request
    ("I want a full refund", "refund_request"),
    ("Can I get my money back?", "refund_request"),
    ("I need a refund", "refund_request"),
    ("Please refund my payment", "refund_request"),
    ("I want to be reimbursed", "refund_request"),
    ("When will I get my refund?", "refund_request"),
    ("I deserve a refund", "refund_request"),
    ("Give me my money back", "refund_request"),
    ("I paid and want a refund", "refund_request"),
    ("How do I get a refund?", "refund_request"),
    ("I was charged and want it back", "refund_request"),
    ("Refund my booking please", "refund_request"),
    ("I expect full compensation", "refund_request"),
    ("My payment should be returned", "refund_request"),
    ("Process a refund for me", "refund_request"),

    # booking_inquiry
    ("What time is check-in?", "booking_inquiry"),
    ("When can I check in?", "booking_inquiry"),
    ("What's my check-out time?", "booking_inquiry"),
    ("Can I see my booking details?", "booking_inquiry"),
    ("What's included in my reservation?", "booking_inquiry"),
    ("I need information about my booking", "booking_inquiry"),
    ("Where is the property located?", "booking_inquiry"),
    ("How do I contact the host?", "booking_inquiry"),
    ("What amenities are included?", "booking_inquiry"),
    ("Is parking available?", "booking_inquiry"),
    ("Can I add more guests?", "booking_inquiry"),
    ("What are the house rules?", "booking_inquiry"),
    ("Is there wifi at the property?", "booking_inquiry"),
    ("How do I get the door code?", "booking_inquiry"),
    ("I need directions to the property", "booking_inquiry"),

    # complaint
    ("The apartment was nothing like the photos", "complaint"),
    ("The place was dirty and disgusting", "complaint"),
    ("There were cockroaches in the kitchen", "complaint"),
    ("The host was rude and unresponsive", "complaint"),
    ("The listing was completely misrepresented", "complaint"),
    ("I'm very unhappy with my stay", "complaint"),
    ("The property was not as described", "complaint"),
    ("There was no hot water", "complaint"),
    ("The photos were completely fake", "complaint"),
    ("The air conditioning was broken", "complaint"),
    ("There was mold everywhere", "complaint"),
    ("I feel unsafe in this property", "complaint"),
    ("The neighborhood is nothing like described", "complaint"),
    ("The bed was broken", "complaint"),
    ("I am extremely disappointed", "complaint"),

    # policy_question
    ("What is the cancellation policy?", "policy_question"),
    ("What does the strict policy mean?", "policy_question"),
    ("How does the moderate policy work?", "policy_question"),
    ("What is the refund policy?", "policy_question"),
    ("What are the cancellation rules?", "policy_question"),
    ("Explain the flexible cancellation policy", "policy_question"),
    ("What happens if I cancel last minute?", "policy_question"),
    ("Is the service fee refundable?", "policy_question"),
    ("What are extenuating circumstances?", "policy_question"),
    ("How many days notice do I need?", "policy_question"),
    ("What is the cleaning fee policy?", "policy_question"),
    ("Can I get a partial refund?", "policy_question"),
    ("What does non-refundable mean?", "policy_question"),
    ("Explain your refund rules", "policy_question"),
    ("What is the 5 day policy?", "policy_question"),

    # escalation_request
    ("I need to speak to a human", "escalation_request"),
    ("Can I talk to a real person?", "escalation_request"),
    ("Connect me to a manager", "escalation_request"),
    ("I want to speak to customer service", "escalation_request"),
    ("This needs human attention", "escalation_request"),
    ("I need a real agent not a bot", "escalation_request"),
    ("Transfer me to someone who can help", "escalation_request"),
    ("I need to escalate this issue", "escalation_request"),
    ("Get me a supervisor", "escalation_request"),
    ("I refuse to deal with a chatbot", "escalation_request"),
    ("I need urgent human assistance", "escalation_request"),
    ("Please connect me to support", "escalation_request"),
    ("I want to file a formal complaint", "escalation_request"),
    ("I need to speak with someone immediately", "escalation_request"),
    ("Put me through to a person", "escalation_request"),

    # general_inquiry
    ("How does Airbnb work?", "general_inquiry"),
    ("How do I leave a review?", "general_inquiry"),
    ("Can I book for someone else?", "general_inquiry"),
    ("How do I update my profile?", "general_inquiry"),
    ("What payment methods do you accept?", "general_inquiry"),
    ("How do I become a host?", "general_inquiry"),
    ("What is Airbnb Plus?", "general_inquiry"),
    ("How do I use a coupon?", "general_inquiry"),
    ("Can I book without a credit card?", "general_inquiry"),
    ("How do I change my password?", "general_inquiry"),
    ("What currencies do you support?", "general_inquiry"),
    ("How do I contact Airbnb?", "general_inquiry"),
    ("What is the guest guarantee?", "general_inquiry"),
    ("How does identity verification work?", "general_inquiry"),
    ("Can I split payment with friends?", "general_inquiry"),

    # out_of_scope
    ("What is the weather in Barcelona?", "out_of_scope"),
    ("Who won the World Cup?", "out_of_scope"),
    ("What should I eat for dinner?", "out_of_scope"),
    ("Tell me a joke", "out_of_scope"),
    ("What is the capital of France?", "out_of_scope"),
    ("How do I learn Python?", "out_of_scope"),
    ("What movies are playing?", "out_of_scope"),
    ("Give me a recipe for pasta", "out_of_scope"),
    ("What time is it?", "out_of_scope"),
    ("Who is the president?", "out_of_scope"),
    ("How do I get to the airport?", "out_of_scope"),
    ("What is Bitcoin?", "out_of_scope"),
    ("Can you write me a poem?", "out_of_scope"),
    ("Translate this to Spanish", "out_of_scope"),
    ("What is the meaning of life?", "out_of_scope"),
]

# ── Build and train classifier ────────────────────────────────────────────────

class MLIntentClassifier:
    """
    Fast TF-IDF + Logistic Regression intent classifier.
    Trained once on startup, runs in <5ms per query.
    """

    CONFIDENCE_THRESHOLD = 0.75

    def __init__(self):
        texts = [item[0] for item in TRAINING_DATA]
        labels = [item[1] for item in TRAINING_DATA]

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=5000,
                sublinear_tf=True,
            )),
            ("clf", LogisticRegression(
                max_iter=1000,
                C=1.0,
                random_state=42,
            )),
        ])
        self.pipeline.fit(texts, labels)
        self.classes = self.pipeline.classes_.tolist()

    def classify(self, message: str) -> dict:
        """
        Classify a message. Returns:
        - primary_intent
        - primary_confidence
        - all_scores dict
        - invoked_llm (False — ML handled it)
        - processing_time_ms
        - should_invoke_llm (True if confidence below threshold)
        """
        start = time.time()

        proba = self.pipeline.predict_proba([message])[0]
        scores = dict(zip(self.classes, [round(float(p), 4) for p in proba]))

        # Sort by confidence
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent = sorted_scores[0][0]
        primary_confidence = sorted_scores[0][1]

        secondary_intent = sorted_scores[1][0] if len(sorted_scores) > 1 else None
        secondary_confidence = sorted_scores[1][1] if len(sorted_scores) > 1 else None

        processing_time = int((time.time() - start) * 1000)
        should_invoke_llm = primary_confidence < self.CONFIDENCE_THRESHOLD

        return {
            "primary_intent": primary_intent,
            "primary_confidence": primary_confidence,
            "secondary_intent": secondary_intent,
            "secondary_confidence": secondary_confidence,
            "all_scores": scores,
            "processing_time_ms": max(processing_time, 1),
            "invoked_llm": False,
            "should_invoke_llm": should_invoke_llm,
            "ml_reason": (
                f"High confidence ({primary_confidence:.0%}) — ML classifier sufficient, LLM not needed"
                if not should_invoke_llm
                else f"Low confidence ({primary_confidence:.0%}) — ambiguous query, invoking LLM for nuanced classification"
            ),
        }


# Singleton — trained once, reused across all requests
_classifier = None

def get_classifier() -> MLIntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = MLIntentClassifier()
    return _classifier
