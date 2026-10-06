"""Converted from risk_detection_recovered.ipynb.
Notebook code cells are preserved in their original order.
Jupyter shell/magic commands are retained as comments so this file is valid Python.
"""

# %% [cell 1]
# CELL 1
# Basic setup

import re

RISK_LEVELS = {
    0: "Low",
    1: "Medium",
    2: "High"
}

print(RISK_LEVELS)


def has_word(text, phrase):

    # Whole-word match: "nsw" must not match inside "answer",
    # "india" must not match inside "indiana"
    return re.search(r"\b" + re.escape(phrase) + r"\b", text) is not None


WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "eighteen": 18,
    "twenty": 20, "twenty-four": 24, "thirty": 30, "thirty-six": 36,
    "forty-eight": 48, "sixty": 60
}

# A duration in years or months:
#   "twenty-four (24) months" / "2.5 years" / "18 months" / "three years"
DURATION_PATTERN = re.compile(
    r"(?:\b[a-z]+(?:-[a-z]+)?\s*\(\s*(\d+(?:\.\d+)?)\s*\)"
    r"|\b(\d+(?:\.\d+)?)"
    r"|\b(" + "|".join(sorted(WORD_NUMBERS, key=len, reverse=True)) + r"))"
    r"\s*(year|month)s?\b"
)


def find_duration(text):

    # Returns (length in years, text to show) or None,
    # e.g. "24 months" -> (2.0, "24 months"), "3 years" -> (3.0, "3 years")
    match = DURATION_PATTERN.search(text)

    if not match:
        return None

    raw = match.group(1) or match.group(2) or match.group(3)
    value = float(raw) if raw[0].isdigit() else WORD_NUMBERS[raw]
    unit = match.group(4)

    if unit == "year":
        return value, f"{value:g} year{'' if value == 1 else 's'}"

    return value / 12, f"{value:g} month{'' if value == 1 else 's'}"

# %% [cell 2]
# CELL 2
# NON-COMPETE RISK DETECTOR

def detect_noncompete_risk(text):

    text_lower = text.lower()

    score = 0
    reasons = []

    # -------------------------------------
    # 1. Detect duration
    # -------------------------------------

    # Years or months, e.g. "three years", "24 months", "2.5 years"
    duration = find_duration(text_lower)

    if duration:

        years, shown = duration

        if years >= 3:

            score += 2

            reasons.append(
                f"Long non-compete duration: {shown}"
            )

        elif years >= 1:

            score += 1

            reasons.append(
                f"Non-compete duration: {shown}"
            )

    # -------------------------------------
    # 2. Detect broad geographic scope
    # -------------------------------------

    broad_geography = [
        "worldwide",
        "anywhere in the world",
        "global",
        "all countries",
        "any country"
    ]

    for phrase in broad_geography:

        if phrase in text_lower:

            score += 2

            reasons.append(
                "Very broad geographic restriction"
            )

            break

    # -------------------------------------
    # 3. Detect broad activity restriction
    # -------------------------------------

    broad_activity = [
        "any competing business",
        "any competitor",
        "directly or indirectly compete",
        "engage in any business"
    ]

    for phrase in broad_activity:

        if phrase in text_lower:

            score += 1

            reasons.append(
                "Broad restriction on competitive activity"
            )

            break

    # -------------------------------------
    # 4. Convert score to risk level
    # -------------------------------------

    if score >= 3:
        risk = "High"

    elif score >= 1:
        risk = "Medium"

    else:
        risk = "Low"

    return {
        "category": "Non-Compete",
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons
    }

# %% [cell 3]
# CELL 3
# TEST NON-COMPETE

sample_clause = """
The employee shall not directly or indirectly compete with
any competitor of the Company anywhere in the world for
three years following termination of employment.
"""

result = detect_noncompete_risk(sample_clause)

print(result)

# %% [cell 4]
def detect_liability_risk(text):

    # Convert to lowercase
    text_lower = text.lower()

    # IMPORTANT:
    # Replace line breaks / multiple spaces with one normal space
    text_lower = re.sub(r"\s+", " ", text_lower)

    score = 0
    reasons = []

    # -------------------------------------
    # 1. Unlimited / uncapped liability
    # -------------------------------------

    unlimited_patterns = [
        r"unlimited liability",
        r"uncapped liability",
        r"liability.{0,40}unlimited",
        r"liability.{0,40}uncapped",
        r"no limit.{0,30}liability",
        r"no limitation.{0,30}liability"
    ]

    unlimited_detected = False

    for pattern in unlimited_patterns:

        if re.search(pattern, text_lower):

            score += 3

            reasons.append(
                "Potential unlimited or uncapped liability"
            )

            unlimited_detected = True
            break

    # -------------------------------------
    # 2. Consequential / indirect damages
    # -------------------------------------

    consequential_terms = [
        "consequential damages",
        "indirect damages",
        "special damages",
        "incidental damages",
        "punitive damages",
        "consequential loss",
        "indirect loss",
        "special loss",
        "incidental loss"
    ]

    # Wording that EXCLUDES these losses ("neither Party is liable for
    # consequential loss") protects the parties instead of exposing them
    exclusion_cues = [
        "not liable",
        "not be liable",
        "no liability",
        "neither party is liable",
        "neither party shall be liable",
        "neither party will be liable",
        "in no event",
        "excluded",
        "exclude"
    ]

    for phrase in consequential_terms:

        if phrase in text_lower:

            # Only look for exclusion wording in the SAME sentence,
            # so "Fees exclude GST." elsewhere does not count
            sentence = next(
                s for s in re.split(r"(?<=[.;])\s+", text_lower) if phrase in s
            )

            if any(cue in sentence for cue in exclusion_cues):

                reasons.append(
                    "Consequential or indirect loss is excluded (protective)"
                )

            else:

                score += 2

                reasons.append(
                    "Exposure to consequential or indirect damages"
                )

            break

    # -------------------------------------
    # 3. Indemnity obligation
    # -------------------------------------

    indemnity_terms = [
        "indemnify",
        "indemnification",
        "hold harmless",
        "defend and indemnify"
    ]

    for phrase in indemnity_terms:

        if phrase in text_lower:

            score += 1

            reasons.append(
                "Indemnity obligation detected"
            )

            break

    # -------------------------------------
    # 4. Liability cap
    # -------------------------------------

    # "shall / will / must / does not exceed", "not to exceed", "limited to"
    cap_patterns = [
        r"liability.{0,100}(?:shall|will|must|does|is to)\s+not\s+exceed",
        r"liability.{0,100}not\s+to\s+exceed",
        r"liability.{0,60}limited to",
        r"maximum liability",
        r"liability cap"
    ]

    cap_detected = False

    for pattern in cap_patterns:

        if re.search(pattern, text_lower):

            cap_detected = True

            reasons.append(
                "Liability cap appears to be present"
            )

            break

    # Reduce risk slightly if there is a cap
    # and no unlimited liability
    if cap_detected and not unlimited_detected and score > 0:
        score -= 1

    # -------------------------------------
    # 5. Risk level
    # -------------------------------------

    if score >= 4:
        risk = "High"

    elif score >= 1:
        risk = "Medium"

    else:
        risk = "Low"

    return {
        "category": "Liability",
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons
    }

# %% [cell 5]
sample_liability = """
The Supplier shall indemnify and hold harmless the Company
from all claims and damages. The Supplier's liability shall
be unlimited and shall include consequential and indirect damages.
"""

result = detect_liability_risk(sample_liability)

print(result)

# %% [cell 6]
# CELL 6
# TERMINATION RISK DETECTOR

def detect_termination_risk(text):

    text_lower = text.lower()
    text_lower = re.sub(r"\s+", " ", text_lower)

    score = 0
    reasons = []

    # -------------------------------------
    # 1. Termination without notice
    # -------------------------------------

    no_notice_patterns = [
        "without notice",
        "immediately terminate",
        "terminate immediately",
        "with immediate effect"
    ]

    # Immediate termination for breach or insolvency is a standard,
    # balanced right, so it is reported but not scored
    standard_triggers = [
        "material breach",
        "insolven",
        "liquidat",
        "bankrupt",
        "administration",
        "receivership",
        "winding up"
    ]

    for phrase in no_notice_patterns:

        if phrase in text_lower:

            if any(trigger in text_lower for trigger in standard_triggers):

                reasons.append(
                    "Immediate termination limited to breach or insolvency (standard)"
                )

            else:

                score += 2

                reasons.append(
                    "Termination may occur without meaningful notice"
                )

            break

    # -------------------------------------
    # 2. Very short notice period
    # -------------------------------------

    word_to_num = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30
    }

    number = (
        r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten|'
        r'eleven|twelve|thirteen|fourteen|fifteen|sixteen|'
        r'seventeen|eighteen|nineteen|twenty|thirty)'
    )

    # Optional "(30)" after a written number, and optional
    # "calendar" / "business" / "working" before "days"
    days_pattern = r"\s*(?:\(\d+\)\s*)?(?:calendar\s+|business\s+|working\s+)?days?"

    # Only a period that is actually a NOTICE period counts, e.g.
    #   "30 calendar days' written notice", "thirty (30) days notice",
    #   "notice of at least 14 days"
    # (not e.g. "fails to remedy the breach within 14 days")
    notice_match = (
        re.search(
            number + days_pattern + r"['’]?\s+(?:prior\s+)?(?:written\s+)?notice",
            text_lower
        )
        or re.search(
            r"notice\s+(?:period\s+)?of\s+(?:at\s+least\s+|not\s+less\s+than\s+)?"
            + number + days_pattern,
            text_lower
        )
    )

    if notice_match:

        value = notice_match.group(1)

        if value.isdigit():
            days = int(value)
        else:
            days = word_to_num[value]

        if days <= 7:

            score += 2

            reasons.append(
                f"Very short termination notice period: {days} days"
            )

        elif days <= 30:

            score += 1

            reasons.append(
                f"Short termination notice period: {days} days"
            )

    # -------------------------------------
    # 3. Termination for convenience
    # -------------------------------------

    convenience_terms = [
        "termination for convenience",
        "terminate for convenience",
        "at its convenience",
        "at any time for any reason"
    ]

    # Also catches wording such as "terminate this Agreement for convenience"
    convenience_pattern = (
        r"terminat\w*\s+(?:this\s+agreement\s+)?for\s+(?:its\s+|their\s+)?convenience"
    )

    if (
        any(phrase in text_lower for phrase in convenience_terms)
        or re.search(convenience_pattern, text_lower)
    ):

        score += 1

        reasons.append(
            "Termination for convenience detected"
        )

    # -------------------------------------
    # 4. One-sided termination language
    # -------------------------------------

    unilateral_terms = [
        "sole discretion",
        "without cause",
        "for any reason or no reason",
        "at any time"
    ]

    # A right given to BOTH parties is balanced, not one-sided
    mutual_terms = [
        "either party",
        "each party",
        "both parties",
        "either of the parties"
    ]

    for phrase in unilateral_terms:

        if phrase in text_lower:

            if any(term in text_lower for term in mutual_terms):

                reasons.append(
                    "Termination right is mutual (applies to both parties)"
                )

            else:

                score += 1

                reasons.append(
                    "Potentially broad unilateral termination right"
                )

            break

    # -------------------------------------
    # 5. Convert score to risk
    # -------------------------------------

    if score >= 3:
        risk = "High"

    elif score >= 1:
        risk = "Medium"

    else:
        risk = "Low"

    return {
        "category": "Termination",
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons
    }

# %% [cell 7]
# CELL 7
# TEST TERMINATION

sample_termination = """
The Company may terminate this Agreement at any time for any reason
or no reason upon five days written notice to the Supplier.
"""

result = detect_termination_risk(sample_termination)

print(result)

# %% [cell 8]
# PAYMENT RISK DETECTOR

def detect_payment_risk(text):

    text_lower = text.lower()
    text_lower = re.sub(r"\s+", " ", text_lower)

    score = 0
    reasons = []

    # -------------------------------------
    # 1. Very short payment deadline
    # -------------------------------------

    # "within 14 days", "within 14 calendar days", "within thirty (30) days"
    payment_match = re.search(
        r'within\s+(?:[a-z]+\s*\(\s*)?(\d+)\)?\s+'
        r'(?:calendar\s+|business\s+|working\s+)?(day|days)',
        text_lower
    )

    if payment_match:

        days = int(payment_match.group(1))

        if days <= 7:

            score += 2

            reasons.append(
                f"Very short payment deadline: {days} days"
            )

        elif days <= 14:

            score += 1

            reasons.append(
                f"Short payment deadline: {days} days"
            )


    # -------------------------------------
    # 2. Late payment penalties
    # -------------------------------------

    late_payment_terms = [
        "late payment fee",
        "late fee",
        "penalty interest",
        "default interest",
        "interest on overdue",
        "interest on unpaid"
    ]

    for phrase in late_payment_terms:

        if phrase in text_lower:

            score += 1

            reasons.append(
                "Late-payment penalty or interest detected"
            )

            break


    # -------------------------------------
    # 3. High interest rate
    # -------------------------------------

    interest_match = re.search(
        r'(\d+(?:\.\d+)?)\s*%\s*(?:per annum|per year|annually)',
        text_lower
    )

    if interest_match:

        interest_rate = float(
            interest_match.group(1)
        )

        if interest_rate >= 15:

            score += 2

            reasons.append(
                f"High payment interest rate detected: {interest_rate}%"
            )

        elif interest_rate >= 10:

            score += 1

            reasons.append(
                f"Elevated payment interest rate detected: {interest_rate}%"
            )


    # -------------------------------------
    # 4. Unilateral price / fee changes
    # -------------------------------------

    unilateral_payment_terms = [
        "sole discretion",
        "change the fees",
        "modify the fees",
        "increase the fees",
        "revise the fees",
        "adjust the fees"
    ]

    for phrase in unilateral_payment_terms:

        if phrase in text_lower:

            score += 1

            reasons.append(
                "Potential unilateral fee or payment change"
            )

            break


    # -------------------------------------
    # 5. Risk level
    # -------------------------------------

    if score >= 3:
        risk = "High"

    elif score >= 1:
        risk = "Medium"

    else:
        risk = "Low"


    return {
        "category": "Payment",
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons
    }

# %% [cell 9]
sample_payment = """
The Customer must pay all invoices within 7 days.
Any overdue amount will incur default interest at 18% per annum.
The Company may increase the fees at its sole discretion.
"""

result = detect_payment_risk(sample_payment)

print(result)

# %% [cell 10]
# CONFIDENTIALITY RISK DETECTOR

def detect_confidentiality_risk(text):

    text_lower = text.lower()
    text_lower = re.sub(r"\s+", " ", text_lower)

    score = 0
    reasons = []

    # -------------------------------------
    # 1. Indefinite confidentiality duration
    # -------------------------------------

    indefinite_terms = [
        "in perpetuity",
        "perpetual",
        "indefinitely",
        "without limitation in time",
        "survive indefinitely"
    ]

    for phrase in indefinite_terms:

        if phrase in text_lower:

            score += 2

            reasons.append(
                "Indefinite confidentiality obligation detected"
            )

            break


    # -------------------------------------
    # 2. Long post-termination survival period
    # -------------------------------------

    # Years or months, e.g. "three years", "60 months"
    duration = find_duration(text_lower)

    if duration:

        years, shown = duration

        if years >= 5:

            score += 2

            reasons.append(
                f"Long confidentiality duration detected: {shown}"
            )

        elif years >= 2:

            score += 1

            reasons.append(
                f"Extended confidentiality duration detected: {shown}"
            )


    # -------------------------------------
    # 3. Very broad confidential information definition
    # -------------------------------------

    broad_terms = [
        "all information",
        "any information",
        "all data",
        "any data",
        "whether confidential or not",
        "of any kind"
    ]

    for phrase in broad_terms:

        if phrase in text_lower:

            score += 1

            reasons.append(
                "Broad definition of confidential information detected"
            )

            break


    # -------------------------------------
    # 4. No obvious exclusions
    # -------------------------------------

    normal_exclusions = [
        "publicly available",
        "public domain",
        "already known",
        "independently developed",
        "lawfully received from a third party"
    ]

    exclusion_found = False

    for phrase in normal_exclusions:

        if phrase in text_lower:

            exclusion_found = True
            break

    if not exclusion_found:

        score += 1

        reasons.append(
            "No standard confidentiality exclusions detected"
        )


    # -------------------------------------
    # 5. Risk level
    # -------------------------------------

    if score >= 3:
        risk = "High"

    elif score >= 1:
        risk = "Medium"

    else:
        risk = "Low"


    return {
        "category": "Confidentiality",
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons
    }

# %% [cell 11]
sample_confidentiality = """
The Receiving Party shall keep all information disclosed by the
Company confidential in perpetuity and shall not disclose such
information to any third party.
"""

result = detect_confidentiality_risk(sample_confidentiality)

print(result)

# %% [cell 12]
# GOVERNING LAW RISK DETECTOR

def detect_governing_law_risk(text):

    text_lower = text.lower()
    text_lower = re.sub(r"\s+", " ", text_lower)

    score = 0
    reasons = []

    # -------------------------------------
    # 1. Foreign governing law / jurisdiction
    # -------------------------------------

    foreign_jurisdictions = [
        "new york",
        "california",
        "delaware",
        "texas",
        "florida",
        "england and wales",
        "united kingdom",
        "singapore",
        "hong kong",
        "india",
        "china",
        "canada",
        "germany",
        "france"
    ]

    foreign_found = None

    for jurisdiction in foreign_jurisdictions:

        if has_word(text_lower, jurisdiction):

            foreign_found = jurisdiction

            score += 2

            reasons.append(
                f"Foreign governing jurisdiction detected: {jurisdiction.title()}"
            )

            break


    # -------------------------------------
    # 2. Exclusive foreign jurisdiction
    # -------------------------------------

    # The look-behinds stop "non-exclusive jurisdiction" (the opposite
    # meaning) from matching "exclusive jurisdiction"
    exclusive_patterns = [
        r"(?<!non-)(?<!non )(?<!non)exclusive jurisdiction",
        r"submit exclusively",
        r"(?<!non-)(?<!non )(?<!non)exclusive venue",
        r"only the courts of"
    ]

    for pattern in exclusive_patterns:

        if re.search(pattern, text_lower):

            score += 1

            reasons.append(
                "Exclusive jurisdiction requirement detected"
            )

            break


    # -------------------------------------
    # 3. Arbitration in foreign location
    # -------------------------------------

    arbitration_terms = [
        "arbitration",
        "arbitral tribunal"
    ]

    arbitration_found = any(
        phrase in text_lower
        for phrase in arbitration_terms
    )

    if arbitration_found and foreign_found:

        score += 1

        reasons.append(
            "Foreign arbitration or dispute resolution may apply"
        )


    # -------------------------------------
    # 4. Australian / NSW governing law
    # -------------------------------------

    local_terms = [
        "new south wales",
        "nsw",
        "australia",
        "commonwealth of australia"
    ]

    local_found = any(
        has_word(text_lower, phrase)
        for phrase in local_terms
    )

    if local_found:

        reasons.append(
            "Australian or NSW governing law detected"
        )

        # reduce concern slightly
        if score > 0:
            score -= 1


    # -------------------------------------
    # 5. Risk level
    # -------------------------------------

    if score >= 3:
        risk = "High"

    elif score >= 1:
        risk = "Medium"

    else:
        risk = "Low"


    return {
        "category": "Governing Law",
        "risk_level": risk,
        "risk_score": score,
        "reasons": reasons
    }

# %% [cell 13]
sample_governing_law = """
This Agreement shall be governed by the laws of the State of New York.
The parties submit to the exclusive jurisdiction of the courts of
New York for all disputes arising out of this Agreement.
"""

result = detect_governing_law_risk(sample_governing_law)

print(result)

# %% [cell 14]
# MASTER RISK DETECTOR

def detect_risk(text, category):

    if category == "Confidentiality":
        return detect_confidentiality_risk(text)

    elif category == "Governing Law":
        return detect_governing_law_risk(text)

    elif category == "Liability":
        return detect_liability_risk(text)

    elif category == "Non-Compete":
        return detect_noncompete_risk(text)

    elif category == "Payment":
        return detect_payment_risk(text)

    elif category == "Termination":
        return detect_termination_risk(text)

    else:
        return {
            "category": category,
            "risk_level": "Unknown",
            "risk_score": 0,
            "reasons": [
                "No risk detector available for this category"
            ]
        }

# %% [cell 15]
sample_clause = """
The Company may terminate this Agreement at any time for any reason
or no reason upon five days written notice to the Supplier.
"""

category = "Termination"

result = detect_risk(
    sample_clause,
    category
)

print(result)

# %% [cell 16]
sample_clause = """
The employee shall not directly or indirectly compete with
any competitor anywhere in the world for three years.
"""

category = "Non-Compete"

result = detect_risk(
    sample_clause,
    category
)

print(result)

# %% [cell 17]
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from pathlib import Path


def find_repo_root():

    # Works on any computer: walk up from this file (or from the current
    # folder when running cell by cell) until the "ml/models" folder is found
    start = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

    for folder in [start, *start.parents]:
        if (folder / "ml" / "models").is_dir():
            return folder

    raise FileNotFoundError("Could not find the ClauseNexa repository (ml/models folder).")


# 7-class model: the 6 categories + "Other" (clauses outside the 6 categories)
model_path = find_repo_root() / "ml" / "models" / "legalbert_classifier_7class"

tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    local_files_only=True
)

model = AutoModelForSequenceClassification.from_pretrained(
    model_path,
    local_files_only=True
)

device = torch.device("cpu")

model.to(device)
model.eval()

print("Legal-BERT loaded successfully.")
print(model.config.id2label)

# %% [cell 18]
def predict_clause_category(text):

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=384
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():
        outputs = model(**inputs)

        probabilities = torch.softmax(
            outputs.logits,
            dim=-1
        )[0]

    predicted_id = torch.argmax(
        probabilities
    ).item()

    predicted_category = model.config.id2label[
        predicted_id
    ]

    confidence = probabilities[
        predicted_id
    ].item()

    return predicted_category, confidence

# %% [cell 19]
sample_clause = """
The Company may terminate this Agreement at any time
for any reason or no reason upon five days written notice.
"""

category, confidence = predict_clause_category(
    sample_clause
)

print("Predicted category:", category)
print("Confidence:", round(confidence, 4))

# %% [cell 20]
def analyze_clause(text, confidence_threshold=0.70):

    # Step 1: Predict category
    category, confidence = predict_clause_category(text)

    # Step 2: Low-confidence fallback
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

    # Step 3: Clause outside the 6 categories (Notices, Assignment, ...)
    # -> no risk rules apply, so do not run a detector on it
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

    # Step 4: Run risk detector
    risk_result = detect_risk(
        text,
        category
    )

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

# %% [cell 21]
sample_clause = """
The employee shall not directly or indirectly compete with
any competitor of the Company anywhere in the world for
three years following termination of employment.
"""

result = analyze_clause(sample_clause)

print(result)

# %% [cell 22]
def analyze_multiple_clauses(clauses):

    results = []

    for i, clause in enumerate(clauses, start=1):

        analysis = analyze_clause(clause)

        analysis["clause_number"] = i

        results.append(analysis)

    return results

# %% [cell 23]
sample_clauses = [
    """
    The employee shall not directly or indirectly compete with
    any competitor anywhere in the world for three years.
    """,

    """
    The Supplier's liability shall be unlimited and shall include
    consequential and indirect damages.
    """,

    """
    The Company may terminate this Agreement upon five days notice
    for any reason or no reason.
    """
]

results = analyze_multiple_clauses(sample_clauses)

for result in results:
    print("\n------------------------------")
    print("Clause Number:", result["clause_number"])
    print("Category:", result["predicted_category"])
    print("Confidence:", result["classification_confidence"])
    print("Risk:", result["risk_level"])
    print("Risk Score:", result["risk_score"])
    print("Reasons:", result["risk_reasons"])

# %% [cell 24]
import re

# "1."  "1)"  "1.1"  "2.3.4"
# A dot or bracket is REQUIRED after a single number, so a wrapped line
# such as "30 days written notice" is not mistaken for a heading
NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+)+\.?|\d+[.)])\s+")

# "Section 4", "Clause 7.2", "Article IV", "ARTICLE 3"
NAMED_HEADING = re.compile(
    r"^(section|clause|article)\s+(\d+(\.\d+)*|[ivxlc]+)\b",
    re.IGNORECASE
)

# A short line fully in capitals: "GOVERNING LAW", "LIMITATION OF LIABILITY"
CAPS_HEADING = re.compile(r"^[A-Z][A-Z0-9 &,'()/\-]{3,}$")

# Page markers from the PDF extractor ("[PAGE 2]") and printed footers ("Page 2", "2 of 10")
PAGE_MARKER = re.compile(r"^\[PAGE\s+\d+\]$", re.IGNORECASE)
PAGE_FOOTER = re.compile(r"^(page\s+)?\d+(\s+of\s+\d+)?$", re.IGNORECASE)


def is_heading(line):

    if NUMBERED_HEADING.match(line) or NAMED_HEADING.match(line):
        return True

    # A capitals line is only a heading if it is short and not a sentence
    return (
        bool(CAPS_HEADING.match(line))
        and len(line.split()) <= 6
        and not line.endswith((".", ";", ",", ":"))
    )


def split_contract_text(contract_text, min_chars=40):

    # -------------------------------------
    # 1. Normalise line endings and remove page markers / footers
    # -------------------------------------

    lines = []

    for raw_line in contract_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):

        line = re.sub(r"\s+", " ", raw_line).strip()

        if line and (PAGE_MARKER.match(line) or PAGE_FOOTER.match(line)):
            continue

        lines.append(line)   # blank lines kept for the fallback in step 3

    # -------------------------------------
    # 2. Group lines into sections:
    #    a heading line starts a new section,
    #    every other line (including "(a)", "(b)" sub-items
    #    and wrapped lines) belongs to the current section
    # -------------------------------------

    sections = []

    for line in lines:

        if not line:
            continue

        if is_heading(line) or not sections:
            sections.append([line])
        else:
            sections[-1].append(line)

    sections = [" ".join(section) for section in sections]

    # -------------------------------------
    # 3. No headings found -> fall back to blank-line paragraphs
    # -------------------------------------

    if len(sections) <= 1:

        sections = [
            re.sub(r"\s+", " ", paragraph).strip()
            for paragraph in re.split(r"\n\s*\n+", "\n".join(lines))
        ]

    # -------------------------------------
    # 4. Merge short fragments into the next section
    #    (e.g. "3. TERMINATION" followed by "3.1 ..."),
    #    and drop a short fragment left at the end (e.g. a signature line)
    # -------------------------------------

    clauses = []
    carry = ""

    for section in sections:

        section = f"{carry} {section}".strip() if carry else section

        if len(section) < min_chars:
            carry = section
            continue

        clauses.append(section)
        carry = ""

    return clauses

# %% [cell 25]
sample_contract_2 = """
1.1 Payment Terms
The Customer shall pay all invoices within 7 days of receipt.
Any overdue amount shall attract interest at 18% per annum.

1.2 Late Payment
The Company may suspend services if any invoice remains unpaid.

2.1 Limitation of Liability
The Supplier's liability shall be unlimited and shall include
consequential and indirect damages.

3. TERMINATION
The Company may terminate this Agreement at any time for any reason
or no reason upon five days written notice.

Section 4 Confidentiality
The Receiving Party shall keep all information confidential in perpetuity.

5.2 Non-Competition
The employee shall not directly or indirectly compete with any competitor
anywhere in the world for three years following termination.
"""

clauses = split_contract_text(sample_contract_2)

print("Number of clauses found:", len(clauses))

for i, clause in enumerate(clauses, start=1):
    print("\n--- Clause", i, "---")
    print(clause)

# %% [cell 26]
results = analyze_multiple_clauses(clauses)

for result in results:

    print("\n================================")

    print("Clause Number:",
          result["clause_number"])

    print("Category:",
          result["predicted_category"])

    print("Confidence:",
          result["classification_confidence"])

    print("Risk:",
          result["risk_level"])

    print("Risk Score:",
          result["risk_score"])

    print("Reasons:",
          result["risk_reasons"])

# %% [cell 27]
from collections import Counter

RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2}

ALL_CATEGORIES = [
    "Confidentiality", "Governing Law", "Liability",
    "Non-Compete", "Payment", "Termination"
]


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
        # (e.g. an employment contract normally has no Liability clause)
        "categories_not_found": [
            category for category in ALL_CATEGORIES
            if category not in category_counts
        ],
        "high_risk_clause_numbers": [
            r["clause_number"] for r in analysed if r["risk_level"] == "High"
        ]
    }


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


def analyze_contract(contract_text):

    # Step 1: Split the contract into clauses
    clauses = split_contract_text(contract_text)

    # Step 2: Classify + risk-check every clause
    results = analyze_multiple_clauses(clauses)

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

# %% [cell 28]
import json

report = analyze_contract(sample_contract_2)

for clause in report["clauses"]:
    print(clause["clause_number"], clause["predicted_category"],
          clause["classification_confidence"], clause["risk_level"], clause["risk_score"])

print(json.dumps(report["summary"], indent=2))

# %% [cell 29]
# Test: a contract that also contains clauses OUTSIDE the 6 categories
# (Notices, Entire Agreement). With the 7-class model these should be
# "Other" and should not get a risk level.
sample_contract_3 = """
EMPLOYMENT AGREEMENT

1. PAYMENT
The Company shall pay all invoices within 7 days. Late payments
accrue default interest at 18% per annum.

2. CONFIDENTIALITY
The Employee shall keep all information confidential in perpetuity.

3. NON-COMPETE
The employee shall not directly or indirectly compete with any competitor
anywhere in the world for three years following termination.

4. TERMINATION
The Company may terminate this Agreement at any time for any reason
or no reason upon five days written notice.

5. LIMITATION OF LIABILITY
The Supplier's liability shall be unlimited and shall include
consequential and indirect damages.

6. GOVERNING LAW
This Agreement is governed by the laws of the State of New York and the
parties submit to the exclusive jurisdiction of the courts of New York.

7. NOTICES
All notices under this Agreement must be in writing and delivered by
hand or email to the addresses set out above.

8. ENTIRE AGREEMENT
This Agreement constitutes the entire agreement between the parties and
supersedes all prior negotiations and understandings.

Signed by the parties.
"""

report_3 = analyze_contract(sample_contract_3)

for clause in report_3["clauses"]:
    print(clause["clause_number"], clause["predicted_category"],
          clause["classification_confidence"], clause["risk_level"], clause["risk_score"])

print(json.dumps(report_3["summary"], indent=2))
