"""
End-to-end contract analysis: clause splitting + Legal-BERT + risk detection.

    contract text
      -> split_contract_text()        -> list of clauses
      -> Legal-BERT (7 classes)       -> category + confidence per clause
      -> confidence < 0.70            -> "Needs Review" (no risk rules run)
      -> category == "Other"          -> "Not Applicable" (outside the 6 categories)
      -> detect_risk()                -> risk level + score + reasons
      -> one JSON-ready dict for the whole contract

Entry points:
    analyze_contract(contract_text)    full contract  <- main backend entry point
    analyze_multiple_clauses(clauses)  list of clause strings
    analyze_clause(text)               one clause

No file, database or API work happens here: text in, plain dicts out, so the
FastAPI backend can return the result directly as JSON.

Copied from: analyze_clause(), analyze_multiple_clauses(), summarize_contract()
and analyze_contract() in risk_detection.py. Same output; the only difference
is that classification is batched (much faster for whole contracts).
"""

from collections import Counter

from .classifier import predict_clause_categories
from .clause_splitter import split_contract_text
from .risk_detector import detect_risk


# Below this confidence a clause is marked "Needs Review"
CONFIDENCE_THRESHOLD = 0.70

RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2}

ALL_CATEGORIES = [
    "Confidentiality", "Governing Law", "Liability",
    "Non-Compete", "Payment", "Termination"
]


# -------------------------------------------------
# 1. ONE CLAUSE  (same as analyze_clause in risk_detection.py)
# -------------------------------------------------

def _build_result(text, category, confidence, confidence_threshold):

    # Low confidence: do not trust the category
    if confidence < confidence_threshold:
        return {
            "clause_text": text.strip(),
            "predicted_category": "Needs Review",
            "suggested_category": category,
            "classification_confidence": round(confidence, 4),
            "risk_level": "Needs Review",
            "risk_score": None,
            "risk_reasons": [
                "Classification confidence is below the review threshold."
            ]
        }

    # Clause outside the 6 categories (Notices, Assignment, ...)
    if category == "Other":
        return {
            "clause_text": text.strip(),
            "predicted_category": "Other",
            "suggested_category": "Other",
            "classification_confidence": round(confidence, 4),
            "risk_level": "Not Applicable",
            "risk_score": None,
            "risk_reasons": [
                "Clause is outside the six analysed categories; no risk rules applied."
            ]
        }

    # One of the 6 categories: run its risk detector
    risk_result = detect_risk(text, category)

    # Every result has the same keys, so the backend/frontend can rely on them
    return {
        "clause_text": text.strip(),
        "predicted_category": category,
        "suggested_category": category,
        "classification_confidence": round(confidence, 4),
        "risk_level": risk_result["risk_level"],
        "risk_score": risk_result["risk_score"],
        "risk_reasons": risk_result["reasons"]
    }


def analyze_clause(text, confidence_threshold=CONFIDENCE_THRESHOLD):
    """Analyse one clause."""

    result = analyze_multiple_clauses([text], confidence_threshold)[0]
    del result["clause_number"]
    return result


# -------------------------------------------------
# 2. MANY CLAUSES  (same as analyze_multiple_clauses, but batched)
# -------------------------------------------------

def analyze_multiple_clauses(clauses, confidence_threshold=CONFIDENCE_THRESHOLD, batch_size=16):
    """Analyse a list of clause strings; results are numbered from 1."""

    clauses = [c for c in clauses if c and c.strip()]
    predictions = predict_clause_categories(clauses, batch_size=batch_size)

    results = []

    for i, (text, (category, confidence)) in enumerate(zip(clauses, predictions), start=1):
        analysis = _build_result(text, category, confidence, confidence_threshold)
        analysis["clause_number"] = i
        results.append(analysis)

    return results


# -------------------------------------------------
# 3. CONTRACT SUMMARY  (same as summarize_contract)
# -------------------------------------------------

def summarize_contract(results):

    # Clauses that passed the confidence check AND belong to one of the
    # 6 categories (only these are risk-checked)
    analysed = [
        r for r in results
        if r["predicted_category"] not in ("Needs Review", "Other")
    ]

    needs_review = [r for r in results if r["predicted_category"] == "Needs Review"]
    other = [r for r in results if r["predicted_category"] == "Other"]

    category_counts = Counter(r["predicted_category"] for r in analysed)
    risk_counts = Counter(r["risk_level"] for r in analysed)

    # Highest risk level found anywhere in the contract
    overall_risk = max(
        (r["risk_level"] for r in analysed if r["risk_level"] in RISK_ORDER),
        key=RISK_ORDER.get,
        default=None
    )

    return {
        "total_clauses": len(results),
        "analysed_clauses": len(analysed),
        "other_clauses": len(other),
        "needs_review_clauses": len(needs_review),
        "overall_risk_level": overall_risk,
        "risk_level_counts": {
            level: risk_counts.get(level, 0) for level in RISK_ORDER
        },
        "category_counts": {
            category: category_counts.get(category, 0) for category in ALL_CATEGORIES
        },
        # Neutral fact, not a risk finding
        "categories_not_found": [
            category for category in ALL_CATEGORIES
            if category not in category_counts
        ],
        "high_risk_clause_numbers": [
            r["clause_number"] for r in analysed if r["risk_level"] == "High"
        ]
    }


# -------------------------------------------------
# 4. CONTRACT-WIDE CONTEXT  (same as apply_contract_context)
# -------------------------------------------------

CONFIDENTIALITY_EXCLUSIONS = [
    "publicly available",
    "public domain",
    "already known",
    "independently developed",
    "lawfully received from a third party"
]

MISSING_EXCLUSIONS_REASON = "No standard confidentiality exclusions detected"


def apply_contract_context(results):

    # Some checks need the whole contract, not one sub-clause.
    # Confidentiality exclusions are often in their own sub-clause
    # (e.g. 6.3), so "missing exclusions" is only true if NO clause
    # in the contract contains them.
    exclusions_in_contract = any(
        phrase in r["clause_text"].lower()
        for r in results
        for phrase in CONFIDENTIALITY_EXCLUSIONS
    )

    if not exclusions_in_contract:
        return results

    for r in results:

        if MISSING_EXCLUSIONS_REASON in r["risk_reasons"]:

            r["risk_reasons"] = [
                reason for reason in r["risk_reasons"]
                if reason != MISSING_EXCLUSIONS_REASON
            ]

            r["risk_score"] -= 1

            # Same thresholds as detect_confidentiality_risk()
            if r["risk_score"] >= 3:
                r["risk_level"] = "High"
            elif r["risk_score"] >= 1:
                r["risk_level"] = "Medium"
            else:
                r["risk_level"] = "Low"

    return results


# -------------------------------------------------
# 5. WHOLE CONTRACT  (same as analyze_contract) — main backend entry point
# -------------------------------------------------

def analyze_contract(contract_text, confidence_threshold=CONFIDENCE_THRESHOLD):
    """
    Analyse a whole contract.

    Returns {"summary": {...}, "clauses": [...], "disclaimer": "..."}
    — plain dicts/lists/str/int/float/None, ready to return as JSON.
    """

    # Step 1: Split the contract into clauses
    clauses = split_contract_text(contract_text)

    # Step 2: Classify + risk-check every clause
    results = analyze_multiple_clauses(clauses, confidence_threshold)

    # Step 3: Re-check rules that depend on the whole contract
    results = apply_contract_context(results)

    # Step 4: Return one JSON-ready result for the whole contract
    return {
        "summary": summarize_contract(results),
        "clauses": results,
        "disclaimer": (
            "Risk levels are automated attention indicators for decision "
            "support, not legal advice."
        )
    }
