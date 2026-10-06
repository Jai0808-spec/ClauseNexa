"""
Legal-BERT clause classifier.

Predicts which of the 7 ClauseNexa classes a clause belongs to:
Confidentiality, Governing Law, Liability, Non-Compete, Payment, Termination,
and Other (any clause outside those 6 categories, e.g. Notices, Assignment).

The model is loaded ONCE (on first use) and reused for every prediction.
Loading takes a few seconds and ~440 MB of memory, so it must not happen per
request when the FastAPI backend calls this module.

Model files: ml/models/legalbert_classifier_7class/ (trained in Colab with
ml/notebooks/train_legalbert_7class_colab.ipynb). Override the location with the
CLAUSENEXA_MODEL_DIR environment variable, e.g. on a server.

Converted from: risk_detection.ipynb (model loading + predict_clause_category)
"""

import os
from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


# ml/src/clausenexa_ml/classifier.py -> parents[2] is the ml/ folder
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "legalbert_classifier_7class"

# Same limit the model was trained with; longer clauses are truncated
MAX_LENGTH = 384


# -------------------------------------------------
# 1. LOAD MODEL (once)
# -------------------------------------------------

@lru_cache(maxsize=1)
def load_model():
    """Load tokenizer + model the first time; later calls return the cached pair."""

    model_dir = os.environ.get("CLAUSENEXA_MODEL_DIR", str(DEFAULT_MODEL_DIR))

    # local_files_only: never try to download from the Hugging Face Hub
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()  # inference mode: disables dropout

    return tokenizer, model, device


# -------------------------------------------------
# 2. PREDICT
# -------------------------------------------------

def predict_clause_category(text):
    """
    Classify one clause.

    Returns (category, confidence), e.g. ("Termination", 0.9999).
    confidence is the softmax probability of the predicted category (0-1).
    """

    return predict_clause_categories([text])[0]


def predict_clause_categories(texts, batch_size=16):
    """
    Classify many clauses at once (much faster than one-by-one).

    Returns a list of (category, confidence) tuples in the same order as texts.
    """

    tokenizer, model, device = load_model()
    results = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        inputs = tokenizer(
            batch,
            return_tensors="pt",
            truncation=True,
            padding=True,          # pad to the longest clause in this batch
            max_length=MAX_LENGTH,
        ).to(device)

        with torch.no_grad():
            probabilities = torch.softmax(model(**inputs).logits, dim=-1)

        confidences, predicted_ids = probabilities.max(dim=-1)

        for confidence, predicted_id in zip(confidences.tolist(), predicted_ids.tolist()):
            results.append((model.config.id2label[predicted_id], confidence))

    return results
