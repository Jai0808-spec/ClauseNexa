"""
Step 5 — Build the 7-class dataset (6 target categories + "Other").

Why: the 6-class Legal-BERT is closed-set — it forces every clause into one of
the 6 categories (e.g. a Notices clause -> Payment, 0.9999). Adding a curated
"Other" class lets the model recognise out-of-scope clauses.

How the Other class is built:
  - 20 curated LEDGAR label groups that are clearly outside the 6 categories
    and common in real contracts (Notices, Entire Agreement, Assignment, ...).
  - Labels semantically close to a target class are deliberately excluded
    (jurisdiction/arbitration, fees/taxes, survival/term, indemnification,
    disclosures, non-solicitation, ...) — see docs/ML_HANDOFF.md.
  - A clause is kept only if ALL its labels belong to ONE Other group, none is a
    target label, and its text is not already in the 6-class dataset.
  - At most 450 clauses per group -> 9,000 balanced, diverse Other clauses
    (17.5% of the final dataset, so Other does not dominate).
  - The last step previews the grouped 70/15/15 split (0 source overlap).

Input:  data/raw/LEDGAR_2016-2019_clean.jsonl
        data/processed/ClauseNexa_LEDGAR_Clean_SingleLabel.csv
Output: data/processed/ClauseNexa_LEDGAR_7Class.csv
        (extra column other_group = which Other group a clause came from)

Run: python ml/scripts/05_build_7class_dataset.py
"""

# %% [STEP 1] Setup: paths, target labels, and the curated "Other" label groups
import json
import pandas as pd

import paths

LEDGAR_PATH = paths.LEDGAR_JSONL
SIX_CLASS_PATH = paths.CLEAN_SINGLE_LABEL_CSV
OUTPUT_PATH = paths.DATA_PROCESSED / "ClauseNexa_LEDGAR_7Class.csv"

RANDOM_STATE = paths.RANDOM_STATE
MAX_PER_GROUP = 450   # cap per Other group -> ~9,000 diverse Other clauses

# LEDGAR labels already used for the 6 target classes (same mapping as the 6-class dataset)
TARGET_LABELS = {
    "terminations", "termination for cause", "termination without cause",
    "notice of termination", "termination of agreements",
    "payments", "payment of obligations", "timing of payments",
    "payments by borrowers", "form of payments",
    "confidentiality", "confidential information", "non-disclosure",
    "nondisclosure", "confidentiality obligations",
    "limitation of liability", "liability", "limitation on liability",
    "limitations on liability", "limited liability", "maximum liability",
    "non-competitions", "noncompetition", "non-competes",
    "non-competition agreements", "non-compete agreements", "non-competition covenants",
    "governing laws", "governing law", "choice of laws", "applicable laws",
}

# Curated Other groups: clearly outside the 6 categories and common in real contracts.
# Group name -> LEDGAR labels belonging to it
OTHER_GROUPS = {
    "Notices": ["notices"],
    "Entire Agreement": ["entire agreements", "integration"],
    "Amendments": ["amendments", "modifications"],
    "Counterparts": ["counterparts"],
    "Waivers": ["waivers", "no waivers"],
    "Severability": ["severability"],
    "Assignment": ["successors", "assigns", "assignments", "binding effects"],
    "Headings": ["headings", "titles"],
    "Definitions": ["definitions", "defined terms"],
    "Interpretation": ["interpretations", "construction"],
    "Further Assurances": ["further assurances"],
    "Representations": ["representations", "warranties"],
    "Authority": ["authority", "authorizations"],
    "No Conflicts": ["no conflicts"],
    "Compliance With Laws": ["compliance with laws"],
    "Insurance": ["insurances", "insurance"],
    "Intellectual Property": ["intellectual property"],
    "Force Majeure": ["force majeure"],
    "Books and Audit": ["books", "records", "audit rights", "audits", "inspections"],
    "Third Party Beneficiaries": ["third party beneficiaries", "no third party beneficiaries"],
}

LABEL_TO_GROUP = {
    label: group
    for group, labels in OTHER_GROUPS.items()
    for label in labels
}

print("Other groups:", len(OTHER_GROUPS))
print("LEDGAR labels used for Other:", len(LABEL_TO_GROUP))


# %% [STEP 2] Collect candidate Other clauses from the full LEDGAR corpus
# A clause is kept only if:
#   - ALL its labels belong to ONE Other group (no mixed-topic clauses)
#   - none of its labels is a target label
#   - its text is not already in the 6-class dataset
six_class_df = pd.read_csv(SIX_CLASS_PATH)
target_texts = set(six_class_df["clause_text"])

rows = []

with open(LEDGAR_PATH, "r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)

        text = str(record.get("provision", "")).strip()
        source = str(record.get("source", "")).strip()
        labels = {str(l).lower().strip() for l in record.get("label", [])}

        if not text or not source:
            continue

        if labels & TARGET_LABELS:
            continue

        groups = {LABEL_TO_GROUP.get(l) for l in labels}

        # Every label must map to the same single Other group
        if len(groups) != 1 or None in groups:
            continue

        if text in target_texts:
            continue

        rows.append({
            "clause_text": text,
            "clause_category": "Other",
            "original_label": "; ".join(sorted(labels)),
            "source": source,
            "other_group": groups.pop(),
        })

candidates_df = pd.DataFrame(rows).drop_duplicates(subset=["clause_text"])

print("Candidate Other clauses:", len(candidates_df))
print(candidates_df["other_group"].value_counts())


# %% [STEP 3] Sample a balanced, diverse Other class
# Take at most MAX_PER_GROUP clauses from each group, so no single
# clause type (e.g. Assignment, with 12k+ clauses) dominates "Other"
other_df = pd.concat(
    [
        group_df.sample(n=min(len(group_df), MAX_PER_GROUP), random_state=RANDOM_STATE)
        for _, group_df in candidates_df.groupby("other_group")
    ],
    ignore_index=True,
)

print("Final Other clauses:", len(other_df))
print("Unique source contracts:", other_df["source"].nunique())
print(other_df["other_group"].value_counts())


# %% [STEP 4] Combine with the 6-class dataset and save
six_class_df["other_group"] = None

df_7 = pd.concat([six_class_df, other_df], ignore_index=True)

# Quality checks
print("Total clauses:", len(df_7))
print("Unique source contracts:", df_7["source"].nunique())
print("Clause texts in more than one class:",
      (df_7.groupby("clause_text")["clause_category"].nunique() > 1).sum())

print("\nClass distribution:")
print(df_7["clause_category"].value_counts())
print("\nClass percentages:")
print((df_7["clause_category"].value_counts(normalize=True) * 100).round(2))

df_7.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print("\nSaved to:", OUTPUT_PATH)


# %% [STEP 5] Preview the grouped 70/15/15 split (no training yet)
from sklearn.model_selection import GroupShuffleSplit

gss_1 = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=RANDOM_STATE)
train_idx, temp_idx = next(gss_1.split(df_7, groups=df_7["source"]))
train_df, temp_df = df_7.iloc[train_idx], df_7.iloc[temp_idx]

gss_2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=RANDOM_STATE)
val_idx, test_idx = next(gss_2.split(temp_df, groups=temp_df["source"]))
val_df, test_df = temp_df.iloc[val_idx], temp_df.iloc[test_idx]

print("Train / Validation / Test:", len(train_df), len(val_df), len(test_df))

train_s, val_s, test_s = set(train_df["source"]), set(val_df["source"]), set(test_df["source"])
print("Source overlap train-val:", len(train_s & val_s),
      "| train-test:", len(train_s & test_s),
      "| val-test:", len(val_s & test_s))

print(pd.DataFrame({
    "train": train_df["clause_category"].value_counts(),
    "val": val_df["clause_category"].value_counts(),
    "test": test_df["clause_category"].value_counts(),
}))
