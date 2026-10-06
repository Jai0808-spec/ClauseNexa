"""
Step 1 — Build the ClauseNexa dataset from the full LEDGAR corpus.

LEDGAR contains ~100k contract provisions from SEC filings, each tagged with one
or more of ~12,000 free-text labels (e.g. "terminations", "governing laws").
This script:

  1. Counts every LEDGAR label and saves the counts to LEDGAR_all_labels.txt.
  2. (Optional, --explore) prints candidate labels per ClauseNexa category, which
     is how the curated LABEL_MAPPING below was chosen by hand.
  3. Maps the curated LEDGAR labels onto the 6 ClauseNexa categories.
  4. Cleans the result (empty values, duplicates) and saves it as
     ClauseNexa_LEDGAR_Final.csv.

Output columns: clause_text, clause_category, original_label, source
  - source = the SEC filing a clause came from. It is used later to split data
    by contract, so clauses from one contract never appear in both train and test.

The output still contains clauses mapped to MORE than one category; those are
removed in 02_clean_single_label.py.

Converted from: Logistic Regression baseline.ipynb (cells 0-3)
Run:            python ml/scripts/01_build_ledgar_dataset.py [--explore]
"""

import argparse
import json
from collections import Counter

import pandas as pd

from paths import LEDGAR_FINAL_CSV, LEDGAR_JSONL, LEDGAR_LABELS_TXT


# -------------------------------------------------
# 1. CURATED LABEL MAPPING
#
# LEDGAR label (lower-case) -> ClauseNexa category.
# Chosen manually from the --explore output: only labels that clearly
# describe the category are included, to keep training labels precise.
# -------------------------------------------------

LABEL_MAPPING = {

    # TERMINATION
    "terminations": "Termination",
    "termination for cause": "Termination",
    "termination without cause": "Termination",
    "notice of termination": "Termination",
    "termination of agreements": "Termination",

    # PAYMENT
    "payments": "Payment",
    "payment of obligations": "Payment",
    "timing of payments": "Payment",
    "payments by borrowers": "Payment",
    "form of payments": "Payment",

    # CONFIDENTIALITY
    "confidentiality": "Confidentiality",
    "confidential information": "Confidentiality",
    "non-disclosure": "Confidentiality",
    "nondisclosure": "Confidentiality",
    "confidentiality obligations": "Confidentiality",

    # LIABILITY
    "limitation of liability": "Liability",
    "liability": "Liability",
    "limitation on liability": "Liability",
    "limitations on liability": "Liability",
    "limited liability": "Liability",
    "maximum liability": "Liability",

    # NON-COMPETE
    "non-competitions": "Non-Compete",
    "noncompetition": "Non-Compete",
    "non-competes": "Non-Compete",
    "non-competition agreements": "Non-Compete",
    "non-compete agreements": "Non-Compete",
    "non-competition covenants": "Non-Compete",

    # GOVERNING LAW
    "governing laws": "Governing Law",
    "governing law": "Governing Law",
    "choice of laws": "Governing Law",
    "applicable laws": "Governing Law",
}


# Keywords used only by --explore to list candidate LEDGAR labels per category
SEARCH_TERMS = {
    "Termination": ["terminat"],
    "Payment": ["payment", "payments", "payable", "fees", "compensation"],
    "Confidentiality": ["confidential", "non-disclosure", "nondisclosure"],
    "Liability": ["liability", "limitation of liability", "limited liability", "damages"],
    "Non-Compete": [
        "non-compete", "noncompete", "non competition", "non-competition",
        "noncompetition", "restrictive covenant", "competition",
    ],
    "Governing Law": ["governing law", "applicable law", "applicable laws", "choice of law"],
}


# -------------------------------------------------
# 2. LABEL EXPLORATION
# -------------------------------------------------

def count_labels(jsonl_path):
    """Count how often every (lower-cased) LEDGAR label occurs."""

    label_counts = Counter()

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)

            for label in record.get("label", []):
                label_counts[label.lower()] += 1

    return label_counts


def save_label_counts(label_counts, output_path):
    """Write 'label<TAB>count' lines, most frequent first."""

    with open(output_path, "w", encoding="utf-8") as out:
        for label, count in label_counts.most_common():
            out.write(f"{label}\t{count}\n")


def print_candidate_labels(label_counts, top_n=30):
    """Print the most frequent LEDGAR labels matching each category's keywords."""

    for category, terms in SEARCH_TERMS.items():

        print("\n" + "=" * 60)
        print(category)
        print("=" * 60)

        matches = [
            (label, count)
            for label, count in label_counts.items()
            if any(term in label for term in terms)
        ]

        for label, count in sorted(matches, key=lambda x: x[1], reverse=True)[:top_n]:
            print(f"{label}: {count}")


# -------------------------------------------------
# 3. BUILD THE CLAUSENEXA DATASET
# -------------------------------------------------

def build_dataset(jsonl_path):
    """
    Read LEDGAR and keep every provision whose label is in LABEL_MAPPING.

    A provision with several mapped labels produces one row per label, which is
    how multi-category clauses enter the dataset (handled in step 2).
    """

    rows = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)

            provision = str(record.get("provision", "")).strip()
            labels = record.get("label", [])
            source = str(record.get("source", "")).strip()

            # Skip empty clause text
            if not provision:
                continue

            # A provision can have more than one label
            for label in labels:
                label_clean = str(label).lower().strip()

                if label_clean in LABEL_MAPPING:
                    rows.append({
                        "clause_text": provision,
                        "clause_category": LABEL_MAPPING[label_clean],
                        "original_label": label_clean,
                        "source": source,
                    })

    return pd.DataFrame(rows)


def clean_dataset(df):
    """Drop empty values and duplicate (clause_text, category) pairs."""

    # Remove missing / empty values
    df = df.dropna(subset=["clause_text", "clause_category", "source"])

    df["clause_text"] = df["clause_text"].astype(str).str.strip()
    df["source"] = df["source"].astype(str).str.strip()

    df = df[(df["clause_text"] != "") & (df["source"] != "")]

    # Remove duplicates: the same clause text with the same category
    # (e.g. boilerplate reused across filings) would otherwise be over-weighted
    before = len(df)
    df = df.drop_duplicates(subset=["clause_text", "clause_category"])
    print("\nDuplicates removed:", before - len(df))

    return df.reset_index(drop=True)


# -------------------------------------------------
# 4. MAIN
# -------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--explore", action="store_true",
                        help="print candidate LEDGAR labels for each category")
    parser.add_argument("--output", default=LEDGAR_FINAL_CSV,
                        help="where to save the mapped dataset CSV")
    args = parser.parse_args()

    # 1. Label counts
    label_counts = count_labels(LEDGAR_JSONL)
    print("Total unique labels:", len(label_counts))

    save_label_counts(label_counts, LEDGAR_LABELS_TXT)
    print("Saved all labels to", LEDGAR_LABELS_TXT)

    if args.explore:
        print_candidate_labels(label_counts)

    # 2. Map LEDGAR labels -> ClauseNexa categories
    df = build_dataset(LEDGAR_JSONL)

    print("\nRaw selected samples:", len(df))
    print("\nRaw class distribution:")
    print(df["clause_category"].value_counts())

    # 3. Clean
    df = clean_dataset(df)

    # 4. Final quality checks
    print("\nFINAL CLASS DISTRIBUTION:")
    print(df["clause_category"].value_counts())
    print("\nTotal final samples:", len(df))
    print("\nMissing values:")
    print(df.isnull().sum())
    print("\nUnique source contracts:", df["source"].nunique())

    # 5. Save (utf-8-sig so Excel opens the CSV correctly)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print("\nFinal ClauseNexa LEDGAR dataset saved to:", args.output)


if __name__ == "__main__":
    main()
