# ClauseNexa - Testing and Evaluation

_Last run: 14 October 2026. All numbers below come from `tests/eval/run_eval.py` and `tests/test_risk_detector.py`; the raw output is in `tests/eval/results.json` and the auto-generated report is `docs/EVALUATION.md`._

---

## 1. Summary

ClauseNexa has four testable layers. The table shows each layer, how it was tested, and the headline result.

| Layer | What it does | How it was tested | Headline result |
|---|---|---|---|
| Clause classification (Legal-BERT, 7 classes) | Labels each clause with one of six categories or "Other" | Held-out test set (7,738 clauses, split by source contract) plus a 72-clause hand-written check | Accuracy 98.84%, macro F1 0.9812; 93.1% agreement on the hand-written check |
| Risk rules | Flags clauses that need attention (Low / Medium / High) | 22 regression tests plus 72 hand-labeled clauses | 22/22 tests pass; accuracy 87.5%; attention-flag F1 95.8% |
| Retrieval | Finds the contract chunks relevant to a question | 37 labeled questions over 4 contracts | P@1 97.3%, MRR 0.987 |
| RAG answers | Generates a grounded answer with citations | 46 labeled questions (37 answerable, 9 unanswerable) | 97.3% correct, 0% hallucination on unanswerable, 94.3% fully faithful |

**Overall assessment.** The pipeline works end to end and the numbers are strong for a prototype. The evaluation sets are small and were written by the team, so they show that the system behaves sensibly, not that it will generalise to arbitrary real contracts (see section 8).

---

## 2. What the proposal committed to, and where it stands

The capstone proposal (Phase 4) promised the metrics below.

| Proposal commitment | Status | Where |
|---|---|---|
| Precision, recall and F1 for clause classification | Done | Section 5.1 |
| TF-IDF + Logistic Regression baseline vs Legal-BERT | Done (6-class baseline; 7-class baseline not built) | Section 5.1 |
| Precision@K for retrieval | Done | Section 5.3 |
| Answer faithfulness | Done (lexical proxy, see limitations) | Section 5.4 |
| Citation correctness | Done | Section 5.4 |
| Functional testing: upload, process, classify, search, query | Done through the API and through the real React UI in an automated test (not by hand in a browser) | Section 6 |
| Error analysis of misclassifications, bad retrievals, unsupported answers | Done | Section 7 |
| Precision / recall for the risk rules | Done (added beyond the original handoff, which had no numbers) | Section 5.2 |

**One documentation correction.** The proposal says the classifier is trained on CUAD. The code and training notebook use **LEDGAR** (grouped by source contract). The final report should say LEDGAR.

---

## 3. Test inventory

| Test asset | Location | Count | Purpose |
|---|---|---|---|
| Risk-rule regression tests | `tests/test_risk_detector.py` | 22 | Every bug found in the risk rules has a test, so it cannot silently return |
| Evaluation contracts | `tests/eval/contracts/` | 4 (services PDF, NDA, employment, lease) | Fictional contracts run through the real upload, process and ask pipeline |
| Question set | `tests/eval/qa_set.json` | 46 (37 answerable, 9 unanswerable) | Retrieval and answer evaluation |
| Risk-clause set | `tests/eval/risk_set.json` | 72 (12 per category) | Risk-rule evaluation and classifier sanity check |
| Evaluation runner | `tests/eval/run_eval.py` | - | Computes all metrics, writes `results.json` and `docs/EVALUATION.md` |
| Live UI test | `frontend/src/App.live.test.js` | 1 (7-step user journey) | Renders the real app against the running backend: upload, overview, clause analysis, ask, off-topic refusal, delete |
| Model training results | `ml/notebooks/train_legalbert_7class_colab.ipynb`, `docs/ML_HANDOFF.md` | - | Held-out classifier metrics |

### How to run

```bash
# Risk-rule regression tests (no model, no server needed)
python tests/test_risk_detector.py

# Full evaluation (backend must be running on port 8000; needs the repo .env)
cd backend && python -m uvicorn app.main:app --port 8000     # terminal 1
python tests/eval/make_contracts.py                           # once, rebuilds the DOCX files
python tests/eval/run_eval.py                                 # terminal 2, about 5 minutes
python tests/eval/run_eval.py --skip-ask                      # retrieval + risk only, about 1 minute
```

```powershell
# Live UI test (backend must be running; skipped when REACT_APP_LIVE_TEST is not set)
cd frontend
$env:REACT_APP_LIVE_TEST=1
npx react-scripts test --watchAll=false --testURL=http://localhost:3000 App.live
```

`--testURL` is required because the backend only allows the origin `http://localhost:3000` (CORS).

The evaluation runner uploads the four test contracts through the real API, measures everything, and deletes its test records afterwards (use `--keep` to retain them).

---

## 4. Metric definitions

| Metric | Definition |
|---|---|
| Precision@K | Fraction of the top K returned chunks that contain the gold clause. With one relevant clause per question, the maximum is 1/K, so raw P@3 and P@5 are capped low. |
| Hit@K | 1 if any of the top K chunks contains the gold clause, else 0 (averaged). |
| MRR | Mean of 1 / rank of the first relevant chunk. |
| Answer correctness | The answer contains at least one expected fact (for example "24,000"). A refusal never counts as correct for an answerable question. |
| Correct abstention | For an unanswerable question, the answer refuses or says the information is not in the contract. |
| Hallucination rate | 1 minus correct abstention: unanswerable questions that received a confident answer. |
| Citation hit rate | The returned sources include a chunk that contains the gold clause. |
| Citation precision | Fraction of returned source chunks that are relevant. |
| Faithfulness (sentence level) | A sentence is supported when at least 70% of its content words appear in the cited chunks, and every number in the answer appears there. This is a lexical proxy, not a logical entailment check. |
| Risk accuracy / macro F1 | Predicted risk level compared with the hand label, for Low / Medium / High. |
| Attention flag | Medium or High treated as "needs attention" against Low. This is the product's core claim, so it is reported separately. |

---

## 5. Results

### 5.1 Clause classification (Legal-BERT)

From the Colab training run, recorded in `docs/ML_HANDOFF.md`. Splits are grouped by source contract with 0 overlap.

| Model | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|
| TF-IDF + Logistic Regression (6-class) | 0.9893 | 0.9816 | 0.9893 |
| Legal-BERT (6-class) | 0.9943 | 0.9886 | 0.9943 |
| **Legal-BERT (7-class, deployed)** | **0.9884** | **0.9812** | **0.9884** |

7-class test F1 per class: Governing Law 0.998, Confidentiality 0.989, Payment 0.987, Other 0.981, Termination 0.981, Liability 0.975, Non-Compete 0.959.

**Sanity check on new wording.** On the 72 hand-written clauses in `risk_set.json`, Legal-BERT agreed with the intended category on **93.1%** (67 of 72), with mean confidence 0.99. The five disagreements were short, ambiguous clauses, for example a mitigation duty labeled Liability but predicted Other, and a survival clause predicted Termination instead of Confidentiality. High confidence on wrong answers (0.998 on one) means the 0.70 review threshold would not have caught them.

**Caveat.** The 6-class and 7-class test sets differ, so their scores are not a strict like-for-like comparison. A 7-class Logistic Regression baseline has not been built.

### 5.2 Risk rules

The risk rules are keyword and regex detectors, so they were tested two ways.

**Regression tests:** 22 of 22 pass.

**Hand-labeled evaluation (72 clauses, 12 per category):**

| Level | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Low | 88.0% | 95.7% | 91.7% | 23 |
| Medium | 82.8% | 88.9% | 85.7% | 27 |
| High | 94.4% | 77.3% | 85.0% | 22 |

Overall accuracy **87.5%**, within one level **98.6%**, macro F1 **0.875**.

**Attention flag (Medium or High vs Low): precision 97.9%, recall 93.9%, F1 95.8%.** Of 49 clauses that need attention, the rules flagged 46, and they wrongly flagged 1 of 23 harmless clauses.

Confusion matrix (rows = expected, columns = predicted):

| | Low | Medium | High |
|---|---|---|---|
| Low | 22 | 1 | 0 |
| Medium | 2 | 24 | 1 |
| High | 1 | 4 | 17 |

Accuracy by category: Non-Compete 91.7%, Liability 91.7%, Termination 91.7%, Governing Law 91.7%, Confidentiality 83.3%, Payment 75.0%.

**Reading this.** The rules are good at the thing the product promises, separating "needs a look" from "fine" (F1 95.8%). They are less reliable at grading severity: High recall is 77%, and 4 of 22 High clauses were rated only Medium. That means the rules err on the side of under-rating severity rather than over-flagging, which is the safer failure for a decision-support tool, but it should be disclosed.

### 5.3 Retrieval (37 answerable questions, 4 contracts)

| Method | P@1 | Hit@1 | MRR | Norm. P@3 | Hit@3 |
|---|---|---|---|---|---|
| Vector search only | 86.5% | 86.5% | 0.932 | 100% | 100% |
| **Hybrid (vector + keyword, deployed)** | **97.3%** | **97.3%** | **0.987** | 100% | 100% |

Raw P@3 is 35.1% and raw P@5 is 21.1% for both methods. This is the arithmetic cap for one-clause questions (a single relevant chunk in the top 3 gives 1/3), not a quality problem; the normalised figures divide by the achievable maximum.

**Important caveat.** The NDA, employment and lease contracts each produce only 2 chunks, so Hit@3 and Hit@5 are trivially 100% for them. Only the services contract (7 chunks) makes retrieval non-trivial, and there both methods scored P@1 = 100% on 10 questions. The reliable evidence for hybrid retrieval is the Hit@1 / MRR gain (86.5% to 97.3%) and the earlier governing-law failure that motivated it (the correct chunk ranked outside the top 5 with vector search alone).

### 5.4 RAG answers (46 questions)

| Metric | Result |
|---|---|
| Answer correctness (37 answerable) | **97.3%** (36 of 37) |
| Citation hit rate | **100%** |
| Citation precision | 43.8% |
| Correct abstention (9 unanswerable) | **100%** |
| Hallucination rate on unanswerable | **0%** |
| Faithfulness, sentence level | 98.1% |
| Fully faithful answers | 94.3% |
| Answers containing a number not in the context | 0 |
| Latency, mean / median / max | 3.8 s / 3.6 s / 6.6 s |

Per contract: services 10/10, NDA 8/9, employment 9/9, lease 9/9.

**Reading this.** Answers are correct and grounded, the system refuses questions the contract cannot answer (including off-topic ones such as "Who is the CEO of Apple?"), and a cited source nearly always contains the answer. Citation precision is low because 5 chunks are returned for a question that usually needs one clause; the user sees extra, less relevant evidence alongside the right one.

### 5.5 Performance

Measured on the development laptop (RTX 4050, 6 GB), models preloaded at startup.

| Step | Time |
|---|---|
| Upload | about 3 s |
| Process (extract, chunk, embed) | about 3 s for a 5-page contract |
| Clause analysis (62 clauses) | about 2.3 s warm |
| Ask a question | 3.8 s mean, 6.6 s max (long list answers such as termination conditions take about 10 s) |

Earlier, on CPU only, answers took 131-237 s each. Moving to the GPU build of PyTorch, capping answer length (240 tokens) and preloading the models brought this to about 4 s. The first request after a cold start loads the models in the background, so start the server and allow about 40 seconds before the first question.

---

## 6. Functional (end-to-end) testing

Exercised in two ways: HTTP calls with real files, and an automated UI test that renders the real React app (jsdom, origin `http://localhost:3000`) against the running backend. **No one has yet clicked through the app in a real browser**, so styling and layout are unchecked.

| Flow | Result |
|---|---|
| `POST /contracts/upload` (PDF and DOCX) | Pass |
| `POST /contracts/{id}/process` (extract, chunk, embed 384-dim, store) | Pass |
| `GET /contracts/{id}` and `GET /contracts` | Pass |
| `GET /contracts/{id}/analysis` (split, classify, risk) | Pass |
| `POST /contracts/{id}/ask` (retrieve, generate, sources) | Pass |
| `DELETE /contracts/{id}` (storage and database cleanup) | Pass |
| CORS preflight from `http://localhost:3000` | Pass |
| Frontend production build | Pass |
| UI: Upload page lists contracts from the backend | Pass |
| UI: choose a DOCX, upload, process, land on Overview | Pass |
| UI: Overview shows the ML summary (overall risk, clause count, needs-review) | Pass |
| UI: Clause Analysis shows classified clause cards and the disclaimer | Pass |
| UI: Ask Contract returns a correct answer ("14 days") with expandable sources containing the exact clause text | Pass |
| UI: off-topic question is refused (no "Tim Cook") | Pass |
| UI: Delete removes the contract from the list and the database | Pass |

The UI test ran in about 7 seconds and left no test data behind. It checks that the right content appears and that the wiring works; it does not check visual design, responsive layout or other browsers.

---

## 7. Error analysis and defects found by testing

Testing found real defects, all fixed unless marked open.

| # | Defect | Found by | Resolution |
|---|---|---|---|
| 1 | Analysis route had a broken string literal, so `contracts.py` failed to parse | First start | Fixed |
| 2 | Governing-law question answered wrongly: vector search ranked the relevant 1,700-character chunk outside the top 5 | Manual testing | Hybrid retrieval (keyword re-rank) |
| 3 | Brevity prompt made the model answer an off-topic question from general knowledge ("Tim Cook") | Re-running questions | Stricter prompt plus a relevance gate that skips the model for unrelated questions |
| 4 | The first relevance gate used raw similarity and wrongly refused 3 of 37 valid questions | Evaluation (similarity scores overlap: valid questions as low as 0.085, unanswerable up to 0.45) | Gate now uses the hybrid score; stemmer improved ("last" now matches "lasts") |
| 5 | Model cited a wrong clause ("Clause 7.4" instead of 6.4) | Faithfulness check | Clause references not present in the retrieved text are removed |
| 6 | Evaluation counted a refusal as a correct answer because the word "not" matched | Reviewing results | Eval tightened: a refusal never counts as correct for an answerable question |
| 7 | Answers took 2-4 minutes on CPU | Timing | GPU build of PyTorch, shorter answers, model preload |
| 8 | Answers cut off lists of conditions (termination answer omitted the breach clause 10.2), reported from a screenshot of the app | Manual use | Answer limit raised to 240 tokens and prompt changed to list every requested condition |
| 9 | Sources shown only as chunk numbers, so users could not verify the evidence (proposal requires showing the source text) | Manual use | API returns each source's text; the Ask page shows expandable sources |
| 10 | Migration 003 clears existing embeddings (column redefined to 384 dimensions) | Migration review | Documented: re-run `/process` for older contracts |

**Open issues found by the evaluation:**

- **Refusal on a valid question:** "Which law governs the NDA?" is answered "does not provide enough information" although the clause is in the retrieved text (the same question was answered correctly under an earlier prompt). The 1.5B answer model is sensitive to prompt wording: across prompt variants, one or two of 37 answerable questions flip between correct and wrong (the lease pets question, the liability cap, and this one). The evaluation set is too small to say which wording is truly best.
- **Payment-days question (earlier run):** the model once answered with the instalment schedule instead of the 14-day deadline. Retrieval was correct; the model picked the wrong clause.
- **Risk-rule misses:** wording the rules do not cover, for example geography phrased "any state or country", liability "capped at ...", obligations that "never expire", unilateral fee changes, late-payment fees and "24 hours' notice". Nine of 72 clauses were misrated.
- **Classifier overconfidence:** a clause wrongly classified at 0.998 confidence passes the 0.70 threshold unflagged.
- **Short-question retrieval:** very short questions embed poorly (similarity as low as 0.085) and rely on the keyword re-rank to be found.

---

## 8. Limitations of this evaluation

1. **Small, self-written data.** Four fictional contracts and 46 questions written by one person (an AI assistant) for this project. The numbers show correct behaviour on clean, well-structured agreements, not on messy real-world PDFs.
2. **Tuned on the test set.** The relevance gate, stemmer and prompt were adjusted after seeing results on these same questions, so the reported numbers are optimistic. A fresh, unseen contract set would give a fairer figure.
3. **Labels need team review.** The 72 risk labels follow the documented scoring rubric in `risk_detector.py` rather than detector output, but they have not been reviewed by the ML owner. At least one label (a 5-year clause with a very broad definition) is arguable.
4. **Faithfulness is lexical.** It measures word overlap with the cited text and will not catch a fluent answer that reverses a meaning (for example an earlier version answered "Yes, pets are allowed" when the lease requires consent; the check flagged it only because other words did not match).
5. **Retrieval is easy at this size.** Most test contracts have 2 chunks, which inflates Hit@K. Longer contracts (20+ pages) are untested.
6. **Single document type per category.** Only services, NDA, employment and lease agreements; no commercial supply, loan or licensing contracts.
7. **Scanned PDFs are untested.** The proposal scopes the prototype to native digital documents.
8. **No load or concurrency testing.** One request at a time; answers run on a single local GPU.

---

## 9. Recommended next steps

1. Click through the app once in a real browser (Chrome) to check layout and styling, which the automated UI test cannot see.
2. Have the ML owner review the 72 risk labels, then fix the missed phrasings listed in section 7.
3. Test on 3-5 real or realistic longer contracts that were not used to tune anything, and report those numbers separately.
4. Add a 7-class Logistic Regression baseline so the classifier comparison is like-for-like.
5. Consider a stronger answer model, or a hosted model for answers only, if yes/no accuracy matters for the demo.
6. Add automated tests to CI (the risk tests are fast and need no model).
7. Record explicit limits in the user interface: answers are decision support, not legal advice (already in the proposal's compliance section).
