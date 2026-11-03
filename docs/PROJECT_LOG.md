# Project Log — ClauseNexa: Legal Contract Analysis and Risk Detection System

Structured to CMMI for Development, Maturity Level 3 (defined process). Every entry comes from the GitHub
repository (`git log`, `README.md`, `docs/TESTING.md`, `docs/EVALUATION.md`, `docs/ML_HANDOFF.md`) or the final
project report (ProjectLibre Gantt, Trello board, Slack screenshots). Where these sources disagree, the
difference is recorded rather than hidden.

## 1. Document control
| Item | Value |
|---|---|
| Project | ClauseNexa – Legal Contract Analysis and Risk Detection System |
| Team | Jai Lodha (lead), Gurpreetsingh Sangari, Eashaan Marwah, Kavyah Bhanushali |
| Supervisor | Dr. Abhijit Dasgupta, S P Jain School of Global Management, Sydney |
| Plan window (Gantt) | 21 Sep – 15 Oct 2026 |
| Repository created | 2026-09-28 |
| Last project commit | 2026-10-14, `aba0f55` — merge of PR #13 (ml-nlp) by Kavyah |
| Final submission | 2026-10-15 |
| Demo / presentation | 2026-11-05 |
| Repository | https://github.com/Jai0808-spec/ClauseNexa |
| Final report | CAPSTONE FINAL PROJECT REPORT (PDF), submitted 15 Oct 2026 |
| Repository size at submission | 36 commits, 7 branches |
| Document author | Jai Lodha |
| Document reviewers | All four team members |
| Approver | Not required |
| Version | 1.0 — final submission, 15 Oct 2026 (history in git) |

## 2. Process-area coverage (maturity level 2 + 3 areas used)
| Area | Where it is addressed |
|---|---|
| REQM Requirements Management | §3 register, traceability to modules |
| RD Requirements Development | §3, proposal commitments in `docs/TESTING.md` §2 |
| PP Project Planning | §4 plan vs Gantt (ProjectLibre, WBS) |
| PMC Project Monitoring & Control | §4 status, §9 activity log, Trello board |
| MA Measurement & Analysis | §10 measures |
| PPQA Process & Product Quality Assurance | §8 peer review and checks |
| CM Configuration Management | §11 |
| TS Technical Solution | §5 decisions, `README.md` §6 |
| PI Product Integration | commit `089e594` "Wire backend, RAG, ML and frontend together" |
| VER Verification / VAL Validation | §7 |
| RSKM Risk Management | §6 |
| DAR Decision Analysis & Resolution | §5 |
| OPD Organizational Process Definition | Slack process post of 6 Oct (§8) |

## 3. Requirements register
| ID | Requirement | Realised in | Verified by |
|---|---|---|---|
| R1 | Upload PDF and DOCX contracts and store them with metadata | `backend/app/routes/contracts.py`, `services/storage.py`, Supabase Storage | API functional test: upload PDF and DOCX — pass |
| R2 | Extract, clean and chunk contract text, keeping page numbers | `rag/.../extractor.py`, `cleaner.py`, `chunker.py`; migration 001 | `/process` functional test — pass |
| R3 | Classify clauses into six categories (Termination, Payment, Confidentiality, Liability, Non-Compete, Governing Law) plus Other | `ml/src/clausenexa_ml/classifier.py`, `clause_splitter.py` | Held-out LEDGAR test set (7,738 clauses); 72-clause hand-written check |
| R4 | TF-IDF + Logistic Regression baseline compared with Legal-BERT | `ml/scripts/03_train_logistic_regression.py`, `04_train_legalbert.py` | 6-class comparison done; **7-class baseline not built** |
| R5 | Rule-based Low / Medium / High risk flags with readable reasons | `ml/src/clausenexa_ml/risk_detector.py`, `contract_analyzer.py` | 22 regression tests; 72 hand-labelled clauses |
| R6 | Contract Q&A with source citations (RAG) | `rag/.../retriever.py`, `generator.py`, `rag.py`; `POST /contracts/{id}/ask` | 46-question evaluation set |
| R7 | Local 384-dimensional embeddings and vector search | `embeddings.py` (all-MiniLM-L6-v2); migrations 002–004 (pgvector, RPC) | Retrieval evaluation (Precision@K, MRR) |
| R8 | Refuse questions the contract cannot answer | relevance gate in `rag.py` | 9 unanswerable questions, incl. off-topic |
| R9 | Four-screen React UI: Upload, Overview, Clause Analysis, Ask Contract | `frontend/src/pages/` | Live UI test `App.live.test.js` (7-step journey) |
| R10 | Not legal advice; disclaimer shown with results | analysis response `disclaimer` field; Overview page | Visual check (report screenshots) |
| R11 | CMMI L3 documentation | this file | Reviewed by all four team members |

## 4. Project plan versus Gantt
Planned dates are read from the ProjectLibre Gantt chart in the report; actual dates come from git commits.

| WBS | Gantt task (planned) | Owner | Actual evidence | Status |
|---|---|---|---|---|
| 1 | Project Proposal Submission (21 Sep) | Jai | Submitted on the Gantt date (team confirmation); Trello card due 1 Oct; proposal referenced in `docs/TESTING.md` §2 | Done (deadline met) |
| 2.1 | First Official Team Meeting (22 Sep) | All | Trello card due 4 Oct; Slack post 6 Oct "first team meeting has been completed" | Done (date differs, see note) |
| 2.2 | Tool Setup — GitHub, Trello, Slack (22 Sep) | Jai | Repo created 28 Sep (`faa7398`) | Done |
| 2.3 | Freeze ClauseNexa MVP & Scope (23 Sep) | Eashaan, Gurpreet, Kavyah | Trello card due 3 Oct | Done |
| 2.4 | Milestone: Architecture & Scope Frozen | — | Planned 24/09 | Met late |
| 3 | Literature Review (24–25 Sep) | Jai, Kavyah | Started once the project topic and domain were finalised; Trello card "Data finding and literature review" due 2 Oct; report §Existing Frameworks and Research | Done |
| 4 | LEDGAR Dataset Collection | Kavyah | `ml/scripts/01_build_ledgar_dataset.py`; first ML upload 28/29 Sep (`25f0acf`) | Done |
| 5 | 7-Class Dataset Cleaning & Preprocessing | Kavyah | `02_clean_single_label.py`, `05_build_7class_dataset.py` | Done |
| 6.1 | Clause Chunker & 384-d MiniLM Embeddings | Gurpreet | `eab511a` 5 Oct, `430a65d` 5 Oct, `f076e51` 6 Oct | Done |
| 6.2 | Supabase pgvector & Cosine Search RPC | Gurpreet, Jai | `11c089c` 7 Oct, migrations 002–004 | Done |
| 6.3 | Legal-BERT & Logistic Regression Training | Kavyah | `a20553d` 6 Oct (PR #10); Colab notebook | Done |
| 6.4 | Rule-Based Risk Detector & Qwen2.5 RAG | Gurpreet, Kavyah | `a20553d` 6 Oct; `13c068e` 7 Oct | Done |
| 6.5 | Milestone: ML & RAG Pipelines Ready | — | Planned 03/10; actual 7 Oct (PR #12) | Met late |
| 7.1 | Frontend (React SPA, Context & 4 Screens) | Eashaan | `cf388bd` 29 Sep; `ba0da0f` 4 Oct (PR #5, #6) | Done |
| 7.2 | Backend (FastAPI Routes & Supabase CRUD) | Jai | `f25d794`, `9889d64`, `2ba9f8d` 28–29 Sep (PR #2–#4) | Done (early) |
| 7.3 | Full-Stack API Wiring & Citation Integration | Eashaan, Gurpreet, Jai | `1e551f7` 5 Oct; `52ce60d` 6 Oct; `089e594` 14 Oct | Done |
| 7.4 | Milestone: Full-Stack MVP Integrated | — | Planned 09/10; actual 14 Oct | Met late |
| 8 | Testing & Evaluation (F1 & Precision@K) | Gurpreet, Kavyah | `7e29ff1` 14 Oct; `docs/EVALUATION.md` | Done |
| 9 | Frontend UAT & Regression Testing | Eashaan, Jai | `App.live.test.js`; defects 8–9 found in manual use; whole team walked through the app on 13–14 Oct (team statement; no written record) | Done (see discrepancy note under §4) |
| 10 | Continuous Documentation (CM3 format) | All | README rewrite `1e7a82a` 14 Oct; docs folder | Done |
| 11 | Final Project Report Compilation | All | Report dated 15 Oct | Done |
| 12 | Project Demo & Presentation Prep | Eashaan, Gurpreet | Demo scheduled for 5 Nov 2026 (after the 15 Oct submission) | Preparation done; demo pending |
| 13 | Final Project Submission (15 Oct) | Jai | Report submitted 15 Oct | Done |

**Schedule note (PMC).** The Gantt planned initiation for 21–24 Sep, but the repository was created on 28 Sep and the
Trello cards for the proposal, scope freeze and first meeting carry due dates of 1–4 Oct. The backend was delivered ahead
of plan (28–29 Sep), while the ML/RAG milestone slipped four days (planned 3 Oct, merged 7 Oct) and full integration slipped
five days (planned 9 Oct, done 14 Oct). Causes are listed in §6 (dataset change, GPU limits, internships). Testing,
documentation and submission still met the 15 Oct deadline.

**Discrepancy note (UAT).** The team states that all four members walked through the app on 13–14 Oct, but the submitted
report ("no manual testing of the entire browser") and `docs/TESTING.md` §6 say no browser walkthrough was done. Both are
recorded here; the written test documents were not updated after the walkthrough.

## 5. Decision log (DAR)
| ID | Decision | Alternatives | Rationale |
|---|---|---|---|
| DEC-001 | Train on LEDGAR only, grouped by source contract (decided 3 Oct 2026) | V1 dataset (CUAD + LEDGAR) | V1 was not good enough for the project and was dropped; grouping prevents train/test leakage. V1 file `data/raw/ClauseNexa_ML_Dataset.csv` kept but unused. |
| DEC-002 | Legal-BERT, 7 classes (6 categories + Other) | 6-class model; TF-IDF + LR only | "Other" stops unrelated clauses being forced into a category; Legal-BERT is domain pre-trained. |
| DEC-003 | Keep TF-IDF + Logistic Regression as baseline | none | Proposal requires a baseline comparison; cheap to train. |
| DEC-004 | Classifier confidence < 0.70 → "Needs Review", no risk rules run | always apply rules | Avoids confident-looking risk flags on uncertain clauses. |
| DEC-005 | Rule-based (keyword/regex) risk detector | learned risk model | Transparent and explainable to non-lawyers; no labelled risk data available. |
| DEC-006 | Local Hugging Face all-MiniLM-L6-v2 embeddings, 384-d | paid embedding API | No API cost; compact vectors (commit `f076e51`, migration 003). |
| DEC-007 | Supabase (PostgreSQL + Storage + pgvector) | separate DB and vector store | One managed service for files, tables and vector search. |
| DEC-008 | Hybrid retrieval: cosine similarity re-ranked with keyword score (weight 0.5), top-k 5 | vector search only | Vector-only search missed a governing-law clause (defect 2); hybrid raised P@1 from 86.5% to 97.3%. |
| DEC-009 | Local answer generation with Qwen2.5-1.5B-Instruct | hosted LLM API | Runs on a 6 GB GPU; no API cost; contract text stays local. |
| DEC-010 | Relevance gate on hybrid score before calling the model | raw similarity gate | Raw similarity wrongly refused 3 of 37 valid questions (defect 4). |
| DEC-011 | Remove clause references not present in the retrieved text | trust model output | Model cited "Clause 7.4" instead of 6.4 (defect 5). |
| DEC-012 | Answer limit 240 tokens; prompt asks for every requested condition | shorter answers | Termination answer omitted clause 10.2 (defect 8). |
| DEC-013 | Run locally with CUDA on team GPUs; no AWS deployment | cloud hosting | Agreed in Slack; CPU answers took 131–237 s, GPU brought this to about 4 s. |
| DEC-014 | Train Legal-BERT on Google Colab | laptop training | Laptops lacked GPU capacity for fine-tuning (`train_legalbert_7class_colab.ipynb`). |
| DEC-015 | React SPA with a central Context provider and a service module | per-page fetching | Avoids duplicate network calls; separates transport from UI. |
| DEC-016 | Large models and datasets git-ignored and shared via Google Drive | commit to GitHub | Files exceed GitHub limits. |

## 6. Risk register (RSKM)
| ID | Risk | Mitigation | Status |
|---|---|---|---|
| RK1 | Initial dataset unsuitable | Switched to LEDGAR (DEC-001) | Closed — resolved in a few days |
| RK2 | No high-end GPU on laptops | Colab for training; local CUDA (6 GB) for inference | Closed |
| RK3 | Slow answers on CPU | GPU PyTorch, model preload, 240-token cap | Closed — mean 3.8 s |
| RK4 | Model hallucinates or answers off-topic | Relevance gate, strict prompt, citation stripping | Mitigated — 0% hallucination on 9 unanswerable |
| RK5 | Rules miss unusual wording | Regression test per bug found | Open — High-risk recall 77% |
| RK6 | Small, team-written test sets overstate quality | Limitations stated in `docs/TESTING.md` §8 and report | Accepted |
| RK7 | Time pressure; members starting internships | Trello due dates, Slack updates, peer-review pairs | Accepted — milestones slipped (§4) |
| RK8 | Confidential contract data | Local processing, temporary storage, delete endpoint | Partly mitigated — no authentication |
| RK9 | Migration 003 clears existing embeddings | Re-run `/process` for older contracts | Documented |

## 7. Verification and validation record
Run on 14 Oct 2026 (`tests/eval/run_eval.py`, `tests/test_risk_detector.py`):

- Risk-rule regression tests: 22 of 22 pass.
- API functional tests: upload, process, list/get, analysis, ask, delete and CORS preflight — all pass.
- Live UI test (`App.live.test.js`): real React app against the running backend — upload, overview, clause analysis, ask, off-topic refusal, delete.
- Evaluation on 4 fictional contracts (services PDF, NDA, employment, lease) with 46 questions (37 answerable, 9 unanswerable) and 72 hand-labelled risk clauses.

Defects found by testing and fixed: 10 (broken route string, vector-only retrieval miss, off-topic answer, over-strict gate,
wrong clause citation, faulty eval scoring, slow CPU answers, truncated lists, sources shown only as numbers, embedding reset
on migration). Full list: `docs/TESTING.md` §7.

Reviews completed after the 14 Oct run: the 72 hand-labelled risk clauses were reviewed by Kavyah and Gurpreet on 12–13 Oct;
the team walkthrough of the app took place on 13–14 Oct (see discrepancy note in §4).

**Not done:** contracts longer than 5 pages; real-world contracts; scanned PDFs; load or concurrency testing; a recorded
manual browser test with written results; 7-class Logistic Regression baseline.

## 8. Quality assurance (PPQA)
Defined process (Slack #workspace, 6 Oct): all work on individual branches; no direct pushes to `main`; a Slack update after
each push (what was done, branch, dependencies, ready for review); a named peer reviewer merges after review; Trello card
moved to Completed with comments and blockers; documentation kept at every major step.

Peer-review allocation: Kavyah → Eashaan, Eashaan → Jai, Jai → Gurpreet, Gurpreet → Kavyah.

Peer reviews were carried out locally on the reviewer's machine, so GitHub holds no review comments or approvals. The only
records are the Slack review requests and confirmations (for example Eashaan's "I have reviewed your work… Looks good" on
Kavyah's ml-nlp push) and the resulting merge commits. This is a known limitation of the review evidence.

## 9. Activity log
| Date | Activity | By |
|---|---|---|
| 2026-09-21 | Project proposal submitted (Gantt date) | Jai |
| 2026-09-22 | First official team meeting and tool setup — GitHub, Trello, Slack (Gantt date; see §4 for the differing Trello and Slack dates) | All |
| 2026-09-23 | ClauseNexa MVP and scope frozen (Gantt date; milestone 24 Sep) | Eashaan, Gurpreet, Kavyah |
| 2026-09-24 to 25 | Literature review (Gantt dates) | Jai, Kavyah |
| 2026-09-28 | Repository and folder structure created (`faa7398`, `2ac4a1e`) | Jai |
| 2026-09-28 | Initial ML files uploaded (PR #1) | Kavyah |
| 2026-09-28 | Supabase schema (PR #2); contract PDF upload API (PR #3) | Jai |
| 2026-09-29 | Contract management API complete (PR #4); file structure updated | Jai |
| 2026-09-29 | React frontend started | Eashaan |
| 2026-10-03 | Dataset switched from the V1 dataset (CUAD + LEDGAR) to LEDGAR only (DEC-001, RK1) | Team |
| 2026-10-04 | Clause Analysis grid and Ask Contract chat UI (PR #5, #6) | Eashaan |
| 2026-10-05 | Frontend connected to backend; contract context and dev scripts | Jai |
| 2026-10-05 | RAG preprocessing, `/process` endpoint, embedding support (PR #7) | Gurpreet |
| 2026-10-06 | Team process posted in Slack (§8); first team meeting confirmed | Jai |
| 2026-10-06 | 7-class Legal-BERT and risk detection layer (PR #10) | Kavyah |
| 2026-10-06 | Upload now calls RAG processing; embeddings switched to local 384-d (PR #9) | Jai, Gurpreet |
| 2026-10-07 | Supabase embeddings resized to 384-d; retrieval; local answer generation; ask endpoint (PR #11, #12) | Gurpreet |
| 2026-10-07 | Backend wiring of Kavyah's work pushed for review | Jai |
| 2026-10-12 to 13 | 72 hand-labelled risk clauses reviewed | Kavyah, Gurpreet |
| 2026-10-13 to 14 | Team walkthrough of the app (UAT) | All |
| 2026-10-14 | Backend, RAG, ML and frontend wired together (AI-assisted) | Jai |
| 2026-10-14 | Evaluation suite, UI test, testing docs; RAG hardened; sources shown (AI-assisted) | Jai |
| 2026-10-14 | README rewritten with full documentation; PR #13 merged | Kavyah |
| 2026-10-15 | Final report submitted | Team |
| 2026-11-05 | Project demo and presentation (scheduled) | Eashaan, Gurpreet |

## 10. Measurement and analysis (MA)
| Measure | Result |
|---|---|
| Legal-BERT 7-class accuracy / macro F1 (held-out, 7,738 clauses) | 0.9884 / 0.9812 |
| Legal-BERT 6-class accuracy / macro F1 | 0.9943 / 0.9886 |
| TF-IDF + LR 6-class accuracy / macro F1 | 0.9893 / 0.9816 |
| Classifier agreement on 72 hand-written clauses | 93.1% |
| Risk rules accuracy / macro F1 | 87.5% / 0.875 |
| Attention flag precision / recall / F1 | 97.9% / 93.9% / 95.8% |
| Retrieval P@1 vector-only → hybrid | 86.5% → 97.3% |
| Retrieval MRR vector-only → hybrid | 0.932 → 0.987 |
| Answer correctness (37 answerable) | 97.3% (36 of 37) |
| Correct abstention / hallucination (9 unanswerable) | 100% / 0% |
| Citation hit rate / citation precision | 100% / 43.8% |
| Fully faithful answers (lexical proxy) | 94.3% |
| Answer latency mean / max (RTX 4050, 6 GB) | 3.8 s / 6.6 s |
| Repository size at submission | 36 commits, 7 branches; merge commits found for PRs #1–#7 and #9–#13 (none for #8) |

Faithfulness is a lexical proxy (70% content-word overlap, all numbers present) and should be read as an upper bound.

### Planned effort per member (derived from the Gantt chart)
Method: for every Gantt task, duration in days × each assigned resource, at 4.5 project hours per working day (an
assumption reflecting part-time capstone work alongside other commitments such as internships; no member exceeds 60 hours
planned). The 16-day "Continuous Documentation" task (WBS 10) is excluded because it is an elapsed span running
alongside other work, not 16 full days of effort per person. These are **planned** figures. Actual hours were not tracked.

| Member | Tasks (WBS) | Planned days | Planned hours |
|---|---|---|---|
| Jai | 1, 2.1, 2.2, 3, 6.2, 7.2, 7.3, 9, 11, 13 | 13.0 | 58.5 |
| Gurpreet | 2.1, 2.3, 6.1, 6.2, 6.4, 7.3, 8, 11, 12 | 10.5 | 47.3 |
| Eashaan | 2.1, 2.3, 7.1, 7.3, 9, 11, 12 | 8.5 | 38.3 |
| Kavyah | 2.1, 2.3, 3, 4, 5, 6.3, 6.4, 8, 11 | 11.0 | 49.5 |

## 11. Configuration management (CM)
Git with feature branches merged to `main` by pull request: `backend`, `frontend`, `frontend-mock-ui`,
`feature/rag-preprocessing`, `rag-llm`, `ml-nlp`. Database changes are versioned as Supabase migrations 001–004.
Git-ignored and shared via Google Drive: Legal-BERT model folders, `*.safetensors`, `*.pt`, the LEDGAR corpus and large
processed CSVs. Also ignored: `.env`, `node_modules/`, virtual environments.
