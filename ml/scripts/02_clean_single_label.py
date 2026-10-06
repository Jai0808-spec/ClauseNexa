"""
Step 2 — Remove ambiguous multi-category clauses (single-label dataset).

Some LEDGAR provisions carry several labels that map to DIFFERENT ClauseNexa
categories (e.g. a clause tagged both "confidentiality" and "non-competitions").
In step 1 such a clause becomes two rows with identical text but different
categories. A single-label classifier cannot learn from that: the same input
would have two "correct" answers.

This script finds every clause text mapped to more than one category and removes
ALL of its rows. Result on the full corpus:
  - 161 ambiguous clause texts -> 322 rows removed
  - 42,681 -> 42,359 clauses, 27,355 unique source contracts

The removed clauses are a known limitation: the final system should eventually
handle clauses with several concepts (multi-label), see docs/ML_HANDOFF.md.

Converted from: Logistic Regression baseline.ipynb (cells 9-11, 19-21)
Run:            python ml/scripts/02_clean_single_label.py [--show-examples]
"""

import argparse

import pandas as pd

from paths import CLEAN_SINGLE_LABEL_CSV, LEDGAR_FINAL_CSV


# -------------------------------------------------
# 1. FIND AMBIGUOUS CLAUSES
# -------------------------------------------------

def find_ambiguous_texts(df):
    """Return the clause texts that are mapped to more than one category."""

    category_counts = df.groupby("clause_text")["clause_category"].nunique()

    return category_counts[category_counts > 1].index


def report_ambiguity(df, ambiguous_texts, show_examples=False):
    """Print how many clauses are ambiguous and, optionally, some examples."""

    print("Clauses mapped to multiple ClauseNexa categories:", len(ambiguous_texts))
    print(
        "Percentage of unique clause texts:",
        round(len(ambiguous_texts) / df["clause_text"].nunique() * 100, 2), "%",
    )

    if show_examples:
        ambiguous_df = (
            df[df["clause_text"].isin(ambiguous_texts)]
            .sort_values("clause_text")
        )

        pd.set_option("display.max_colwidth", 200)
        print(
            ambiguous_df[["clause_text", "clause_category", "original_label"]]
            .head(30)
            .to_string(index=False)
        )


# -------------------------------------------------
# 2. MAIN
# -------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=LEDGAR_FINAL_CSV,
                        help="dataset produced by 01_build_ledgar_dataset.py")
    parser.add_argument("--output", default=CLEAN_SINGLE_LABEL_CSV,
                        help="where to save the single-label dataset")
    parser.add_argument("--show-examples", action="store_true",
                        help="print 30 ambiguous rows for manual inspection")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    print("Original dataset shape:", df.shape)

    # 1. Find and report ambiguous clause texts
    ambiguous_texts = find_ambiguous_texts(df)
    report_ambiguity(df, ambiguous_texts, args.show_examples)

    # 2. Remove every row of an ambiguous clause
    df_clean = df[~df["clause_text"].isin(ambiguous_texts)].copy()

    print("\nOriginal dataset size:", len(df))
    print("Clean dataset size:", len(df_clean))
    print("Removed rows:", len(df) - len(df_clean))

    print("\nClass distribution:")
    print(df_clean["clause_category"].value_counts())
    print("\nUnique source contracts:", df_clean["source"].nunique())

    # 3. Save
    df_clean.to_csv(args.output, index=False, encoding="utf-8-sig")
    print("\nClean dataset saved to:", args.output)


if __name__ == "__main__":
    main()
