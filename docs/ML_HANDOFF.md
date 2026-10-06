# ClauseNexa — ML/NLP Handoff

Reference for the ML/NLP clause-analysis layer: what it does, where everything lives, how to use it, and what is still open. Last updated 2026-10-06.

---

## 1. What this layer does

```
contract text  (from the RAG team's extract_document() + clean_text())
  → split_contract_text()    one item per clause
  → Legal-BERT (7 classes)   category + confidence
  → confidence < 0.70        "Needs Review"   (no risk rules run)
  → category == "Other"      "Not Applicable" (clause outside the 6 categories)
  → detect_risk()            risk level + score + reasons
  → contract-wide context    e.g. confidentiality exclusions found in another sub-clause
  → JSON-ready report        {"summary": {...}, "clauses": [...], "disclaimer": "..."}
```

The 7 classes: Confidentiality, Governing Law, Liability, Non-Compete, Payment, Termination, **Other**.

Risk levels are generic contractual *attention indicators* for decision support — never legal conclusions. They have not yet been validated against Australian/NSW legal sources.

**Not part of this layer:** PDF upload and storage, Supabase writes, RAG retrieval, Sentence Transformer embeddings (~768-dim, pgvector), frontend. The 384-token Legal-BERT limit is unrelated to the RAG embeddings.

---

## 2. Backend usage

```bash
pip install -e ml
```

```python
from clausenexa_ml import analyze_contract

report = analyze_contract(contract_text)   # plain dicts/lists, return directly from FastAPI
```

- The model loads once on first use (~440 MB) from `ml/models/legalbert_classifier_7class/`; override with the `CLAUSENEXA_MODEL_DIR` environment variable.
- Every clause result has the same keys: `clause_number`, `clause_text`, `predicted_category`, `suggested_category`, `classification_confidence`, `risk_level`, `risk_score`, `risk_reasons`.
- `risk_level` is one of `High`, `Medium`, `Low`, `Needs Review`, `Not Applicable`.
- **DB mapping needed** (`supabase/schema.sql`): `detected_clauses.clause_type` expects `termination`, `payment`, `confidentiality`, `liability`, `non_compete`, `governing_law`; `risk_flags.risk_level` only allows `low` / `attention` / `high` (map `Medium` → `attention`); `risk_flags` stores one `risk_reason` per row. "Other" and "Needs Review" clauses have no matching `clause_type`. This mapping belongs in the backend.

---

## 3. File layout

| Path | Contents |
|---|---|
| `ml/src/clausenexa_ml/` | **Backend package**: `clause_splitter.py`, `classifier.py`, `risk_detector.py`, `contract_analyzer.py` |
| `ml/notebooks/risk_detection.py` | Working/experiment file (`# %%` cells). Same logic as the package — keep both in sync |
| `ml/notebooks/train_legalbert_7class_colab.ipynb` | Colab training notebook for the 7-class model, **with the training outputs saved** |
| `ml/scripts/` | Reproducible pipeline: `01_build_ledgar_dataset.py` → `02_clean_single_label.py` → `03_train_logistic_regression.py` → `04_train_legalbert.py` (6-class) → `05_build_7class_dataset.py`; all paths in `paths.py` |
| `tests/test_risk_detector.py` | 22 regression tests for the risk rules (`python tests/test_risk_detector.py`) |
| `ml/models/logistic_regression/` | 6-class TF-IDF + Logistic Regression baseline (in git) |
| `ml/models/legalbert_classifier_7class/` | **Production model** (git-ignored — share via Drive) |
| `ml/models/legalbert_classifier/` | Previous 6-class model, kept as backup (git-ignored) |
| `data/raw/LEDGAR_2016-2019_clean.jsonl` | Full LEDGAR corpus, 710 MB (git-ignored) |
| `data/processed/` | Generated datasets (the three large CSVs are git-ignored), `LEDGAR_all_labels.txt`, Logistic Regression error analysis |
| `data/sample_contracts/sample_contract.pdf` | Fictional 5-page services agreement used for end-to-end testing |

Git-ignored files (models, LEDGAR corpus, large CSVs) are shared through Google Drive — see below.

### Getting the model and datasets (Google Drive)

**Drive folder:** https://drive.google.com/drive/folders/1YMumMjaAxOW3784Ytr0H_rbDTC7p-b0G?usp=drive_link

| Drive file | Put it at | Needed for |
|---|---|---|
| Model zip (`ClauseNexa-…zip`, ~387 MB) | `ml/models/legalbert_classifier_7class/` (6 files) | **Required** to run `analyze_contract()` |
| `ClauseNexa_LEDGAR_7Class.csv` | `data/processed/` | Retraining / evaluating the 7-class model |
| `ClauseNexa_LEDGAR_Clean_SingleLabel.csv` | `data/processed/` | 6-class model and Logistic Regression baseline |
| `ClauseNexa_LEDGAR_Final.csv` | `data/processed/` | Rebuilding the single-label dataset (`02_clean_single_label.py`) |

The model zip contains the path `ClauseNexa/models/legalbert_classifier_7class/`, so extracting it into the folder that **contains** your `ClauseNexa` repository puts the model in the right place. Check that `ml/models/legalbert_classifier_7class/` then holds `config.json`, `label_mapping.json`, `model.safetensors`, `tokenizer.json`, `tokenizer_config.json` and `training_args.bin`.

---

## 4. Data

- **6-class dataset:** full LEDGAR (846,274 provisions, 60,540 contracts) mapped to 6 categories → 42,681 clauses; 161 clause texts mapped to two categories removed (322 rows) → **42,359 clauses, 27,355 contracts** (`ClauseNexa_LEDGAR_Clean_SingleLabel.csv`).
  Governing Law 20,512 · Termination 7,223 · Payment 6,033 · Confidentiality 5,481 · Liability 1,722 · Non-Compete 1,388.
- **7-class dataset** (`ClauseNexa_LEDGAR_7Class.csv`): + 9,000 "Other" clauses = **51,359 clauses, 29,268 contracts**, Other = 17.5%.
  - 20 curated LEDGAR label groups × 450 clauses: Notices, Entire Agreement, Assignment, Amendments, Counterparts, Waivers, Severability, Headings, Definitions, Interpretation, Further Assurances, Representations, Authority, No Conflicts, Compliance With Laws, Insurance, Intellectual Property, Force Majeure, Books and Audit, Third Party Beneficiaries.
  - Deliberately **excluded** (too close to a target class): jurisdiction/venue, jury-trial waiver, arbitration, enforceability, miscellaneous/general, fees/expenses, salary, taxes/withholdings, interest, use of proceeds, vesting, survival, term, effectiveness, change in control, death/disability, employment, indemnification, releases, remedies, specific performance, litigation, disclosures, publicity, non-solicitation.
  - A clause is kept only if all its labels belong to one Other group, none is a target label, and its text is not in the 6-class data.
- All splits are **grouped by source contract** (0 overlap).

---

## 5. Models and results

| Model | Split | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|---|
| TF-IDF + Logistic Regression (6-class) | grouped 80/20; 5-fold StratifiedGroupKFold CV Macro F1 0.9781 | 0.9893 | 0.9816 | 0.9893 |
| Legal-BERT (6-class) | grouped 70/15/15 | 0.9943 | 0.9886 | 0.9943 |
| **Legal-BERT (7-class)** | grouped 70/15/15 (35,993 / 7,628 / 7,738) | **0.9884** | **0.9812** | **0.9884** |

- Base model `nlpaueb/legal-bert-base-uncased`, `max_length=384` (token lengths: median 94, p95 403; 5.84% > 384), 3 epochs, batch 8, lr 2e-5, weight decay 0.01, fp16 on a Colab T4, best epoch by validation Macro F1.
- 7-class validation Macro F1: 0.9709 → **0.9789 (epoch 2, kept)** → 0.9784.
- 7-class test F1 per class: Governing Law 0.9977 · Confidentiality 0.9892 · Payment 0.9865 · Other 0.9808 · Termination 0.9806 · Liability 0.9750 · Non-Compete 0.9586.
- Key confusions: Other → Payment 0 (the old Notices → Payment problem is gone); Other ↔ Termination 12/9 (Assignment, Amendments wording); Non-Compete → Confidentiality 9; Liability → Other 6.
- Hardest Other groups: Assignment 93.8%, Interpretation 94.5%, Amendments 94.8%; 12 of 20 groups at 100% (incl. Force Majeure).
- Hand-written test clauses: **10/10** (Notices, Entire Agreement, Assignment, Force Majeure → Other; one per original category correct).
- The 6- and 7-class test sets differ, so their scores are not a strict like-for-like comparison.

---

## 6. Risk rules

Six keyword/regex detectors (Non-Compete, Liability, Termination, Payment, Confidentiality, Governing Law), each returning `{category, risk_level, risk_score, reasons}`. Rules and scoring are commented in `ml/src/clausenexa_ml/risk_detector.py`.

Fixed after testing on the sample contract and a bug review (each covered by a test):
non-exclusive jurisdiction no longer read as exclusive · "calendar/business days" and "thirty (30) days" · only real notice periods count (not remedy periods) · "terminate this Agreement for convenience" · "will/must not exceed" caps · excluded consequential loss marked protective (same-sentence check) · confidentiality exclusions recognised across sub-clauses · immediate termination for breach/insolvency treated as standard · whole-word jurisdiction matching ("nsw" ≠ "answer", "india" ≠ "Indiana") · durations in months and decimals · mutual termination rights not flagged as one-sided · same output keys on every clause.

Sample contract result: 57 clauses, 28 risk-checked, 29 Other, 3 Medium flags (14-day payment, termination for convenience on 30 days, 3-year confidentiality), overall Medium.

---

## 7. Open work

1. **Measure the risk rules**: hand-label 50–100 clauses (LEDGAR + sample contracts) and report precision/recall — currently there are no numbers.
2. **More test contracts** (employment, NDA, lease, services) — only one tested so far.
3. **Tune the 0.70 confidence threshold** on validation data.
4. **7-class Logistic Regression baseline** for a fair comparison with the 7-class Legal-BERT.
5. **Share models and large datasets** with the team (Drive).
6. Known limitations: survival, indemnity and dispute-resolution clauses get inconsistent labels (excluded from training); multi-topic clauses not handled; "the cap does not apply to …" is reported as "cap present"; very short sentences merge into the neighbouring clause; Australian/NSW legal alignment pending.
7. Later NLP work: party detection (who carries an obligation), broader negation handling, plain-English explanations.
8. `data/raw/ClauseNexa_ML_Dataset.csv` belongs to the dropped V1 (CUAD + LEDGAR) dataset and is unused, but it is tracked in git — remove only after agreeing with the team.

---

## 8. Working style for this workstream

- Explain each major step before giving code; test each step before moving on.
- Never delete or move files without a backup and the owner's approval.
