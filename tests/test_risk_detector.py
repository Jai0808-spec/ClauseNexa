"""
Regression tests for the ClauseNexa risk detectors (ml/src/clausenexa_ml).

Every bug found so far has a test here, so it cannot silently come back.
No model is needed: these tests only check the rule-based risk detectors.

Run from the repository root, either:
    python tests/test_risk_detector.py
    python -m pytest tests/
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ml", "src"))

from clausenexa_ml.risk_detector import detect_risk  # noqa: E402


def check(category, text, level, score, must_include=(), must_exclude=()):
    result = detect_risk(text, category)
    reasons = " | ".join(result["reasons"])

    assert result["risk_level"] == level, f"{level} expected, got {result}"
    assert result["risk_score"] == score, f"score {score} expected, got {result}"

    for part in must_include:
        assert part in reasons, f"'{part}' missing from {result['reasons']}"
    for part in must_exclude:
        assert part not in reasons, f"'{part}' should not be in {result['reasons']}"


# -------------------------------------------------
# 1. Original examples from risk_detection.ipynb (must never change)
# -------------------------------------------------

def test_original_noncompete():
    check("Non-Compete",
          "The employee shall not directly or indirectly compete with any competitor of the Company "
          "anywhere in the world for three years following termination of employment.",
          "High", 5, ["Long non-compete duration: 3 years"])


def test_original_liability():
    check("Liability",
          "The Supplier shall indemnify and hold harmless the Company from all claims and damages. "
          "The Supplier's liability shall be unlimited and shall include consequential and indirect damages.",
          "High", 6, ["Exposure to consequential or indirect damages"])


def test_original_termination():
    check("Termination",
          "The Company may terminate this Agreement at any time for any reason or no reason "
          "upon five days written notice to the Supplier.",
          "High", 4, ["Very short termination notice period: 5 days"])


def test_original_payment():
    check("Payment",
          "The Customer must pay all invoices within 7 days. Any overdue amount will incur default "
          "interest at 18% per annum. The Company may increase the fees at its sole discretion.",
          "High", 6)


def test_original_confidentiality():
    check("Confidentiality",
          "The Receiving Party shall keep all information disclosed by the Company confidential in "
          "perpetuity and shall not disclose such information to any third party.",
          "High", 4)


def test_original_governing_law():
    check("Governing Law",
          "This Agreement shall be governed by the laws of the State of New York. The parties submit "
          "to the exclusive jurisdiction of the courts of New York for all disputes arising out of this Agreement.",
          "High", 3)


# -------------------------------------------------
# 2. Fixes from the first real-contract test
# -------------------------------------------------

def test_non_exclusive_jurisdiction_is_not_exclusive():
    check("Governing Law",
          "The Parties submit to the non-exclusive jurisdiction of the courts of New South Wales.",
          "Low", 0, must_exclude=["Exclusive jurisdiction"])


def test_calendar_days_notice():
    check("Termination",
          "Either Party may terminate this Agreement for convenience by giving 30 calendar days' "
          "written notice to the other Party.",
          "Medium", 2, ["Short termination notice period: 30 days", "Termination for convenience"])


def test_remedy_period_is_not_a_notice_period():
    check("Termination",
          "Either Party may terminate this Agreement immediately by written notice if the other Party "
          "commits a material breach and fails to remedy that breach within 14 calendar days after "
          "receiving written notice.",
          "Low", 0, must_exclude=["notice period"])


def test_payment_calendar_days():
    check("Payment", "The Client must pay a valid invoice within 14 calendar days of the invoice date.",
          "Medium", 1, ["Short payment deadline: 14 days"])


def test_cap_with_will_not_exceed():
    check("Liability",
          "Each Party's total aggregate liability arising out of or in connection with this Agreement "
          "will not exceed the total fees paid or payable.",
          "Low", 0, ["Liability cap appears to be present"])


def test_excluded_consequential_loss_is_protective():
    check("Liability",
          "To the maximum extent permitted by law, neither Party is liable to the other for indirect, "
          "incidental, special or consequential loss, including loss of profit.",
          "Low", 0, ["excluded (protective)"])


def test_insolvency_termination_is_standard():
    check("Termination",
          "Either Party may terminate immediately if the other Party becomes insolvent or enters liquidation.",
          "Low", 0, ["breach or insolvency (standard)"])


# -------------------------------------------------
# 3. Bugs 1-8 from the second review
# -------------------------------------------------

def test_bug1_nsw_not_matched_inside_answer():
    check("Governing Law",
          "This Agreement is governed by the laws of the State of New York. "
          "Each party must answer any claim promptly.",
          "Medium", 2, ["New York"], must_exclude=["Australian or NSW"])


def test_bug2_india_not_matched_inside_indiana():
    check("Governing Law",
          "This Agreement is governed by the laws of New South Wales. Notices to the Indiana office.",
          "Low", 0, ["Australian or NSW"], must_exclude=["India"])


def test_bug3_noncompete_in_months():
    check("Non-Compete",
          "The Employee shall not, for twenty-four (24) months after termination, engage in any "
          "competing business anywhere in Australia.",
          "Medium", 2, ["Non-compete duration: 24 months"])


def test_bug3_long_noncompete_in_months():
    check("Non-Compete", "The Employee shall not compete with the Company for 36 months.",
          "Medium", 2, ["Long non-compete duration: 36 months"])


def test_bug4_decimal_years():
    check("Non-Compete", "The Employee shall not compete with the Company for 2.5 years after termination.",
          "Medium", 1, ["Non-compete duration: 2.5 years"], must_exclude=["duration: 5 years"])


def test_bug5_exclude_in_other_sentence_does_not_count():
    check("Liability",
          "The Supplier's liability is unlimited and includes consequential damages. Fees exclude GST.",
          "High", 5, ["Exposure to consequential or indirect damages"], must_exclude=["protective"])


def test_bug6_mutual_termination_is_not_unilateral():
    check("Termination",
          "Either party may terminate this Agreement at any time by giving 90 days' written notice.",
          "Low", 0, ["mutual"], must_exclude=["unilateral"])


def test_bug6_one_sided_termination_still_flagged():
    check("Termination", "The Company may terminate this Agreement at any time.",
          "Medium", 1, ["unilateral"])


def test_bug7_confidentiality_in_months():
    check("Confidentiality",
          "These obligations continue for sixty (60) months after termination. They do not apply to "
          "information that is publicly available.",
          "Medium", 2, ["Long confidentiality duration detected: 60 months"])


# -------------------------------------------------
# Run without pytest
# -------------------------------------------------

if __name__ == "__main__":
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_")]
    failed = 0

    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as error:
            failed += 1
            print(f"FAIL  {name}\n      {error}")

    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
