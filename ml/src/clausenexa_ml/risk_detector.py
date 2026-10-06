"""
Rule-based risk / attention detection for classified contract clauses.

After Legal-BERT predicts a clause's category, detect_risk(text, category)
runs that category's detector. Every detector returns the same structure:

    {
        "category":   "Non-Compete",
        "risk_level": "High" | "Medium" | "Low",
        "risk_score": 5,
        "reasons":    ["Long non-compete duration: 3 years", ...],
    }

How scoring works: each detector checks a few indicators; every indicator found
adds points to risk_score and a human-readable reason. The total score is then
converted into a risk level. Within one indicator group, only the first matching
phrase counts, so a clause is not penalised twice for saying the same thing.

IMPORTANT: these are generic contractual ATTENTION indicators (V1 keyword /
regex rules), not legal conclusions. They never say a clause is invalid or
unenforceable. The Australian/Sydney-facing version must be validated against
reliable Australian legal sources.

Converted from: risk_detection.ipynb (recovered from the unsaved VS Code tab).
Behaviour change vs the notebook: every detector now collapses line breaks and
repeated spaces before matching (the notebook did this for only 4 of the 6),
so phrases split across lines in PDF text are still found.
"""

import re


# -------------------------------------------------
# 1. SHARED HELPERS
# -------------------------------------------------

# Written-out numbers that appear in durations ("three years", "thirty days")
WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30,
}

# Written numbers used in durations ("three years", "twenty-four (24) months")
DURATION_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "eighteen": 18,
    "twenty": 20, "twenty-four": 24, "thirty": 30, "thirty-six": 36,
    "forty-eight": 48, "sixty": 60,
}

# A duration in years or months:
#   "twenty-four (24) months" / "2.5 years" / "18 months" / "three years"
DURATION_PATTERN = re.compile(
    r"(?:\b[a-z]+(?:-[a-z]+)?\s*\(\s*(\d+(?:\.\d+)?)\s*\)"
    r"|\b(\d+(?:\.\d+)?)"
    r"|\b(" + "|".join(sorted(DURATION_WORD_NUMBERS, key=len, reverse=True)) + r"))"
    r"\s*(year|month)s?\b"
)


def find_duration(text):
    """
    Return (length in years, text to show) or None.
    "24 months" -> (2.0, "24 months"), "3 years" -> (3.0, "3 years")
    """

    match = DURATION_PATTERN.search(text)

    if not match:
        return None

    raw = match.group(1) or match.group(2) or match.group(3)
    value = float(raw) if raw[0].isdigit() else DURATION_WORD_NUMBERS[raw]
    unit = match.group(4)

    if unit == "year":
        return value, f"{value:g} year{'' if value == 1 else 's'}"

    return value / 12, f"{value:g} month{'' if value == 1 else 's'}"


def has_word(text, phrase):
    """Whole-word match: "nsw" must not match inside "answer", "india" inside "indiana"."""

    return re.search(r"\b" + re.escape(phrase) + r"\b", text) is not None


def normalise(text):
    """Lower-case and collapse line breaks / repeated spaces into one space."""

    return re.sub(r"\s+", " ", text.lower())


def to_number(value):
    """Convert '3' or 'three' into 3."""

    return int(value) if value.isdigit() else WORD_TO_NUM[value]


def first_match(text, phrases):
    """Return True if any phrase occurs in the text."""

    return any(phrase in text for phrase in phrases)


def score_to_level(score, high_threshold=3):
    """
    Convert a score into a risk level.
    Most detectors use High >= 3; Liability uses High >= 4 because a single
    unlimited-liability finding already scores 3.
    """

    if score >= high_threshold:
        return "High"
    if score >= 1:
        return "Medium"
    return "Low"


def make_result(category, score, reasons, high_threshold=3):
    return {
        "category": category,
        "risk_level": score_to_level(score, high_threshold),
        "risk_score": score,
        "reasons": reasons,
    }


# -------------------------------------------------
# 2. NON-COMPETE
#
# +2  duration >= 3 years   (+1 for 1-2 years)
# +2  very broad geography  (worldwide, any country ...)
# +1  broad activity restriction
# -------------------------------------------------

NONCOMPETE_BROAD_GEOGRAPHY = [
    "worldwide", "anywhere in the world", "global", "all countries", "any country",
]

NONCOMPETE_BROAD_ACTIVITY = [
    "any competing business", "any competitor",
    "directly or indirectly compete", "engage in any business",
]


def detect_noncompete_risk(text):
    text_lower = normalise(text)
    score, reasons = 0, []

    # 1. Duration of the restriction (years or months)
    duration = find_duration(text_lower)
    if duration:
        years, shown = duration

        if years >= 3:
            score += 2
            reasons.append(f"Long non-compete duration: {shown}")
        elif years >= 1:
            score += 1
            reasons.append(f"Non-compete duration: {shown}")

    # 2. Geographic scope
    if first_match(text_lower, NONCOMPETE_BROAD_GEOGRAPHY):
        score += 2
        reasons.append("Very broad geographic restriction")

    # 3. Scope of restricted activity
    if first_match(text_lower, NONCOMPETE_BROAD_ACTIVITY):
        score += 1
        reasons.append("Broad restriction on competitive activity")

    return make_result("Non-Compete", score, reasons)


# -------------------------------------------------
# 3. LIABILITY
#
# +3  unlimited / uncapped liability
# +2  consequential / indirect / punitive damages
# +1  indemnity obligation
# -1  a liability cap is present (only if liability is NOT unlimited)
# High threshold is 4 (see score_to_level)
# -------------------------------------------------

# ".{0,40}" allows a few words in between, e.g. "liability ... shall be unlimited"
LIABILITY_UNLIMITED_PATTERNS = [
    r"unlimited liability",
    r"uncapped liability",
    r"liability.{0,40}unlimited",
    r"liability.{0,40}uncapped",
    r"no limit.{0,30}liability",
    r"no limitation.{0,30}liability",
]

LIABILITY_CONSEQUENTIAL_TERMS = [
    "consequential damages", "indirect damages", "special damages",
    "incidental damages", "punitive damages",
    "consequential loss", "indirect loss", "special loss", "incidental loss",
]

# Wording that EXCLUDES those losses ("neither Party is liable for
# consequential loss") protects the parties instead of exposing them
LIABILITY_EXCLUSION_CUES = [
    "not liable", "not be liable", "no liability",
    "neither party is liable", "neither party shall be liable",
    "neither party will be liable", "in no event", "excluded", "exclude",
]

LIABILITY_INDEMNITY_TERMS = [
    "indemnify", "indemnification", "hold harmless", "defend and indemnify",
]

# "shall / will / must / does not exceed", "not to exceed", "limited to"
LIABILITY_CAP_PATTERNS = [
    r"liability.{0,100}(?:shall|will|must|does|is to)\s+not\s+exceed",
    r"liability.{0,100}not\s+to\s+exceed",
    r"liability.{0,60}limited to",
    r"maximum liability",
    r"liability cap",
]


def detect_liability_risk(text):
    text_lower = normalise(text)
    score, reasons = 0, []

    # 1. Unlimited / uncapped liability
    unlimited_detected = any(re.search(p, text_lower) for p in LIABILITY_UNLIMITED_PATTERNS)
    if unlimited_detected:
        score += 3
        reasons.append("Potential unlimited or uncapped liability")

    # 2. Consequential / indirect damages: exposure, unless they are excluded
    #    (exclusion wording must be in the SAME sentence, so "Fees exclude GST."
    #    elsewhere in the clause does not count)
    phrase = next((p for p in LIABILITY_CONSEQUENTIAL_TERMS if p in text_lower), None)
    if phrase:
        sentence = next(s for s in re.split(r"(?<=[.;])\s+", text_lower) if phrase in s)
        if first_match(sentence, LIABILITY_EXCLUSION_CUES):
            reasons.append("Consequential or indirect loss is excluded (protective)")
        else:
            score += 2
            reasons.append("Exposure to consequential or indirect damages")

    # 3. Indemnity obligation
    if first_match(text_lower, LIABILITY_INDEMNITY_TERMS):
        score += 1
        reasons.append("Indemnity obligation detected")

    # 4. Liability cap: reported as a reason, and lowers the score slightly,
    #    but only when liability is not also described as unlimited
    cap_detected = any(re.search(p, text_lower) for p in LIABILITY_CAP_PATTERNS)
    if cap_detected:
        reasons.append("Liability cap appears to be present")

        if not unlimited_detected and score > 0:
            score -= 1

    return make_result("Liability", score, reasons, high_threshold=4)


# -------------------------------------------------
# 4. TERMINATION
#
# +2  termination without notice / immediately
# +2  notice <= 7 days   (+1 for 8-30 days)
# +1  termination for convenience
# +1  one-sided / unilateral termination wording
# -------------------------------------------------

TERMINATION_NO_NOTICE = [
    "without notice", "immediately terminate", "terminate immediately", "with immediate effect",
]

# Immediate termination for breach or insolvency is a standard, balanced
# right, so it is reported but not scored
TERMINATION_STANDARD_TRIGGERS = [
    "material breach", "insolven", "liquidat", "bankrupt",
    "administration", "receivership", "winding up",
]

_NUMBER = (
    r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty|thirty)"
)

# Optional "(30)" after a written number, optional "calendar"/"business"/"working"
_DAYS = r"\s*(?:\(\d+\)\s*)?(?:calendar\s+|business\s+|working\s+)?days?"

# Only a period that is actually a NOTICE period counts, e.g.
#   "30 calendar days' written notice", "thirty (30) days notice",
#   "notice of at least 14 days"
# (not e.g. "fails to remedy the breach within 14 days")
TERMINATION_NOTICE_PATTERNS = [
    re.compile(_NUMBER + _DAYS + r"['’]?\s+(?:prior\s+)?(?:written\s+)?notice"),
    re.compile(
        r"notice\s+(?:period\s+)?of\s+(?:at\s+least\s+|not\s+less\s+than\s+)?" + _NUMBER + _DAYS
    ),
]

TERMINATION_CONVENIENCE = [
    "termination for convenience", "terminate for convenience",
    "at its convenience", "at any time for any reason",
]

# Also catches wording such as "terminate this Agreement for convenience"
TERMINATION_CONVENIENCE_PATTERN = re.compile(
    r"terminat\w*\s+(?:this\s+agreement\s+)?for\s+(?:its\s+|their\s+)?convenience"
)

TERMINATION_UNILATERAL = [
    "sole discretion", "without cause", "for any reason or no reason", "at any time",
]

TERMINATION_MUTUAL = ["either party", "each party", "both parties", "either of the parties"]


def detect_termination_risk(text):
    text_lower = normalise(text)
    score, reasons = 0, []

    # 1. No meaningful notice (unless only for breach / insolvency)
    if first_match(text_lower, TERMINATION_NO_NOTICE):
        if first_match(text_lower, TERMINATION_STANDARD_TRIGGERS):
            reasons.append("Immediate termination limited to breach or insolvency (standard)")
        else:
            score += 2
            reasons.append("Termination may occur without meaningful notice")

    # 2. Length of the notice period
    notice_match = next(
        (m for m in (p.search(text_lower) for p in TERMINATION_NOTICE_PATTERNS) if m), None
    )
    if notice_match:
        days = to_number(notice_match.group(1))

        if days <= 7:
            score += 2
            reasons.append(f"Very short termination notice period: {days} days")
        elif days <= 30:
            score += 1
            reasons.append(f"Short termination notice period: {days} days")

    # 3. Termination for convenience
    if (
        first_match(text_lower, TERMINATION_CONVENIENCE)
        or TERMINATION_CONVENIENCE_PATTERN.search(text_lower)
    ):
        score += 1
        reasons.append("Termination for convenience detected")

    # 4. One-sided termination right
    #    (a right given to BOTH parties is balanced, not one-sided)
    if first_match(text_lower, TERMINATION_UNILATERAL):
        if first_match(text_lower, TERMINATION_MUTUAL):
            reasons.append("Termination right is mutual (applies to both parties)")
        else:
            score += 1
            reasons.append("Potentially broad unilateral termination right")

    return make_result("Termination", score, reasons)


# -------------------------------------------------
# 5. PAYMENT
#
# +2  payment due within <= 7 days   (+1 for 8-14 days)
# +1  late-payment fee / penalty interest
# +2  interest rate >= 15% p.a.      (+1 for 10-14.99%)
# +1  unilateral fee changes
# -------------------------------------------------

# "within 14 days", "within 14 calendar days", "within thirty (30) days"
PAYMENT_DEADLINE_PATTERN = re.compile(
    r"within\s+(?:[a-z]+\s*\(\s*)?(\d+)\)?\s+(?:calendar\s+|business\s+|working\s+)?(day|days)"
)

# "18% per annum", "12.5 % annually"
PAYMENT_INTEREST_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*(?:per annum|per year|annually)"
)

PAYMENT_LATE_TERMS = [
    "late payment fee", "late fee", "penalty interest",
    "default interest", "interest on overdue", "interest on unpaid",
]

PAYMENT_UNILATERAL_TERMS = [
    "sole discretion", "change the fees", "modify the fees",
    "increase the fees", "revise the fees", "adjust the fees",
]


def detect_payment_risk(text):
    text_lower = normalise(text)
    score, reasons = 0, []

    # 1. Payment deadline
    deadline_match = PAYMENT_DEADLINE_PATTERN.search(text_lower)
    if deadline_match:
        days = int(deadline_match.group(1))

        if days <= 7:
            score += 2
            reasons.append(f"Very short payment deadline: {days} days")
        elif days <= 14:
            score += 1
            reasons.append(f"Short payment deadline: {days} days")

    # 2. Late-payment penalties
    if first_match(text_lower, PAYMENT_LATE_TERMS):
        score += 1
        reasons.append("Late-payment penalty or interest detected")

    # 3. Interest rate
    interest_match = PAYMENT_INTEREST_PATTERN.search(text_lower)
    if interest_match:
        interest_rate = float(interest_match.group(1))

        if interest_rate >= 15:
            score += 2
            reasons.append(f"High payment interest rate detected: {interest_rate}%")
        elif interest_rate >= 10:
            score += 1
            reasons.append(f"Elevated payment interest rate detected: {interest_rate}%")

    # 4. One party can change fees
    if first_match(text_lower, PAYMENT_UNILATERAL_TERMS):
        score += 1
        reasons.append("Potential unilateral fee or payment change")

    return make_result("Payment", score, reasons)


# -------------------------------------------------
# 6. CONFIDENTIALITY
#
# +2  indefinite / perpetual obligation
# +2  duration >= 5 years   (+1 for 2-4 years)
# +1  very broad definition of confidential information
# +1  none of the standard exclusions (public domain, already known, ...)
# -------------------------------------------------

CONFIDENTIALITY_INDEFINITE = [
    "in perpetuity", "perpetual", "indefinitely",
    "without limitation in time", "survive indefinitely",
]

CONFIDENTIALITY_BROAD = [
    "all information", "any information", "all data", "any data",
    "whether confidential or not", "of any kind",
]

# Exclusions a balanced confidentiality clause normally contains
CONFIDENTIALITY_EXCLUSIONS = [
    "publicly available", "public domain", "already known",
    "independently developed", "lawfully received from a third party",
]


def detect_confidentiality_risk(text):
    text_lower = normalise(text)
    score, reasons = 0, []

    # 1. Obligation never ends
    if first_match(text_lower, CONFIDENTIALITY_INDEFINITE):
        score += 2
        reasons.append("Indefinite confidentiality obligation detected")

    # 2. Long survival period (years or months)
    duration = find_duration(text_lower)
    if duration:
        years, shown = duration

        if years >= 5:
            score += 2
            reasons.append(f"Long confidentiality duration detected: {shown}")
        elif years >= 2:
            score += 1
            reasons.append(f"Extended confidentiality duration detected: {shown}")

    # 3. Very broad definition
    if first_match(text_lower, CONFIDENTIALITY_BROAD):
        score += 1
        reasons.append("Broad definition of confidential information detected")

    # 4. Missing standard exclusions
    if not first_match(text_lower, CONFIDENTIALITY_EXCLUSIONS):
        score += 1
        reasons.append("No standard confidentiality exclusions detected")

    return make_result("Confidentiality", score, reasons)


# -------------------------------------------------
# 7. GOVERNING LAW
#
# +2  foreign (non-Australian) governing law / jurisdiction
# +1  exclusive jurisdiction requirement
# +1  arbitration combined with a foreign jurisdiction
# -1  Australian / NSW law mentioned (reduces concern)
# -------------------------------------------------

GOVERNING_LAW_FOREIGN = [
    "new york", "california", "delaware", "texas", "florida",
    "england and wales", "united kingdom", "singapore", "hong kong",
    "india", "china", "canada", "germany", "france",
]

# The look-behinds stop "non-exclusive jurisdiction" (the opposite meaning)
# from matching "exclusive jurisdiction"
GOVERNING_LAW_EXCLUSIVE = [
    r"(?<!non-)(?<!non )(?<!non)exclusive jurisdiction",
    r"submit exclusively",
    r"(?<!non-)(?<!non )(?<!non)exclusive venue",
    r"only the courts of",
]

GOVERNING_LAW_ARBITRATION = ["arbitration", "arbitral tribunal"]

GOVERNING_LAW_LOCAL = [
    "new south wales", "nsw", "australia", "commonwealth of australia",
]


def detect_governing_law_risk(text):
    text_lower = normalise(text)
    score, reasons = 0, []

    # 1. Foreign governing law (first match only)
    foreign_found = next((j for j in GOVERNING_LAW_FOREIGN if has_word(text_lower, j)), None)
    if foreign_found:
        score += 2
        reasons.append(f"Foreign governing jurisdiction detected: {foreign_found.title()}")

    # 2. Exclusive jurisdiction
    if any(re.search(p, text_lower) for p in GOVERNING_LAW_EXCLUSIVE):
        score += 1
        reasons.append("Exclusive jurisdiction requirement detected")

    # 3. Arbitration outside Australia
    if foreign_found and first_match(text_lower, GOVERNING_LAW_ARBITRATION):
        score += 1
        reasons.append("Foreign arbitration or dispute resolution may apply")

    # 4. Australian / NSW law
    if any(has_word(text_lower, phrase) for phrase in GOVERNING_LAW_LOCAL):
        reasons.append("Australian or NSW governing law detected")

        if score > 0:
            score -= 1

    return make_result("Governing Law", score, reasons)


# -------------------------------------------------
# 8. MASTER DISPATCHER
# -------------------------------------------------

# Category name (exactly as Legal-BERT predicts it) -> detector
DETECTORS = {
    "Confidentiality": detect_confidentiality_risk,
    "Governing Law": detect_governing_law_risk,
    "Liability": detect_liability_risk,
    "Non-Compete": detect_noncompete_risk,
    "Payment": detect_payment_risk,
    "Termination": detect_termination_risk,
}


def detect_risk(text, category):
    """Run the risk detector that matches the clause's predicted category."""

    detector = DETECTORS.get(category)

    if detector is None:
        return {
            "category": category,
            "risk_level": "Unknown",
            "risk_score": 0,
            "reasons": ["No risk detector available for this category"],
        }

    return detector(text)
