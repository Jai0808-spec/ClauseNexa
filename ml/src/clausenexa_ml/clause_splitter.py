"""
Split contract text into individual clauses for classification.

Input:  plain contract text, e.g. the output of the RAG team's
        extract_document() + clean_text() ("[PAGE n]" markers are removed).
Output: list of clause strings, in document order.

Rules:
  - A new clause starts at a heading line: "1." "1)" "1.1" "2.3.4",
    "Section 4", "Clause 7", "Article IV", or a short ALL-CAPS line.
  - Sub-items "(a)", "(b)" and wrapped lines stay with the clause above.
  - A plain number without "." or ")" ("30 days ...") is NOT a heading.
  - Page markers and printed page footers are dropped.
  - No headings at all -> blank lines are used as clause breaks.
  - Fragments shorter than min_chars are merged into the next clause
    (or dropped at the end, e.g. a signature line).

Copied from: split_contract_text() in risk_detection.py (cell 24)
"""

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
