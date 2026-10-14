"""
ClauseNexa evaluation harness - fills the metric gaps listed in the proposal:

  1. Retrieval:   Precision@K, Hit@K, MRR (vector-only vs hybrid)
  2. RAG answers: answer correctness, abstention / hallucination on
                  unanswerable questions, citation correctness, faithfulness
  3. Risk rules:  per-level precision / recall / F1 on hand-labeled clauses
  4. Classifier:  agreement of Legal-BERT with the labeled categories

Needs the backend running (it uploads the evaluation contracts through the
real API) and the repo's .env for Supabase. Test contracts are deleted again
afterwards unless --keep is given.

    python tests/eval/run_eval.py                 # from the repo root
    python tests/eval/run_eval.py --skip-ask      # retrieval + risk only (fast)

Writes tests/eval/results.json and docs/EVALUATION.md.
"""

import argparse
import json
import os
import re
import statistics as st
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml" / "src"))
sys.path.insert(0, str(ROOT / "rag" / "src"))

load_dotenv(ROOT / ".env")

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

LEVELS = ["Low", "Medium", "High"]
KS = (1, 3, 5)

ABSTAIN = re.compile(
    r"does not (provide|specify|mention|contain|include|state|say)"
    r"|not (provide|mention|specif|contain|include|state|enough information|stated|addressed)"
    r"|could not find|cannot (find|determine)|no (relevant|information|mention)"
    r"|there is no|^no\b[,.]|\bno (such|automatic|parking|non-compete|clause)"
    r"|isn't|doesn't|don't",
    re.IGNORECASE,
)

STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "that", "this", "with", "from",
    "will", "must", "may", "can", "has", "have", "had", "not", "any", "all",
    "its", "their", "than", "then", "also", "such", "which", "who", "whom",
    "shall", "under", "into", "other", "each", "per", "per", "contract",
    "agreement", "clause", "according", "states", "stated", "specifically",
}


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------

def norm(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().lower()


def stem(word: str) -> str:
    return word[:5]


def content_stems(text: str) -> set[str]:
    return {
        stem(w)
        for w in re.findall(r"[a-z0-9]+", norm(text))
        if len(w) > 2 and w not in STOPWORDS
    }


def numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def mean(values):
    return round(sum(values) / len(values), 4) if values else None


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


# ---------------------------------------------------------------------
# 1+2. retrieval and RAG answers
# ---------------------------------------------------------------------

def upload_and_process(base_url, path: Path) -> str:
    with open(path, "rb") as fh:
        response = requests.post(
            f"{base_url}/contracts/upload",
            files={"file": (path.name, fh, CONTENT_TYPES[path.suffix])},
            timeout=120,
        )
    response.raise_for_status()
    contract_id = response.json()["contract_id"]

    response = requests.post(f"{base_url}/contracts/{contract_id}/process", timeout=600)
    response.raise_for_status()
    return contract_id


def split_sentences(answer: str) -> list[str]:
    parts = re.split(r"\n+|(?<=[.!?])\s+", answer)
    cleaned = [re.sub(r"^[\s\-*\d.)]+", "", p.replace("**", "")).strip() for p in parts]
    return [p for p in cleaned if len(p) > 3]


def faithfulness(answer: str, context: str) -> dict:
    """
    Lexical groundedness proxy (not an NLI model): a sentence is supported
    when >= 70% of its content words occur in the retrieved context, and
    every number in the answer must occur in the context.
    """

    ctx_stems = content_stems(context)
    ctx_numbers = numbers(context)
    sentences = split_sentences(answer)
    supported = 0

    for sentence in sentences:
        stems = content_stems(sentence)
        if not stems:
            supported += 1
            continue
        if len(stems & ctx_stems) / len(stems) >= 0.7:
            supported += 1

    ungrounded_numbers = sorted(numbers(answer) - ctx_numbers)

    return {
        "sentences": len(sentences),
        "supported": supported,
        "score": supported / len(sentences) if sentences else 1.0,
        "ungrounded_numbers": ungrounded_numbers,
        "fully_faithful": supported == len(sentences) and not ungrounded_numbers,
    }


def eval_rag(base_url, ask, supabase, qa_set):
    from clausenexa_rag.retriever import retrieve_contract_sections

    retrieval_rows, answer_rows, contract_ids, chunk_counts = [], [], [], {}

    for filename, questions in qa_set["contracts"].items():
        print(f"\n== {filename}: upload + process", flush=True)
        contract_id = upload_and_process(base_url, HERE / "contracts" / filename)
        contract_ids.append(contract_id)

        chunks = (
            supabase.table("contract_sections")
            .select("chunk_index, section_text")
            .eq("contract_id", contract_id)
            .order("chunk_index")
            .execute()
            .data
        )
        chunk_text = {c["chunk_index"]: c["section_text"] for c in chunks}
        chunk_counts[filename] = len(chunks)

        for item in questions:
            question = item["q"]
            answerable = item.get("answerable", True)

            candidates = retrieve_contract_sections(
                supabase, contract_id, question, top_k=10
            )
            by_vector = sorted(
                candidates, key=lambda c: c.get("similarity") or 0, reverse=True
            )

            relevant = set()
            if answerable:
                gold = norm(item["gold"])
                relevant = {i for i, t in chunk_text.items() if gold in norm(t)}

            row = {
                "contract": filename,
                "q": question,
                "answerable": answerable,
                "relevant_chunks": sorted(relevant),
                "hybrid_top": [c["chunk_index"] for c in candidates[:5]],
                "vector_top": [c["chunk_index"] for c in by_vector[:5]],
                "best_similarity": max(
                    (c.get("similarity") or 0 for c in candidates), default=0
                ),
            }
            if answerable and not relevant:
                row["mapping_error"] = "gold text not found in any chunk"

            retrieval_rows.append(row)

            if ask:
                started = time.time()
                response = requests.post(
                    f"{base_url}/contracts/{contract_id}/ask",
                    json={"question": question},
                    timeout=300,
                )
                seconds = time.time() - started
                body = response.json()
                answer = body.get("answer", f"HTTP {response.status_code}: {body}")
                sources = [s["chunk_index"] for s in body.get("sources", [])]
                context = "\n".join(chunk_text.get(i, "") for i in sources)
                abstained = bool(ABSTAIN.search(answer.strip()))

                record = {
                    "contract": filename,
                    "q": question,
                    "answerable": answerable,
                    "answer": answer,
                    "sources": sources,
                    "seconds": round(seconds, 2),
                    "abstained": abstained,
                }

                gate_refusal = answer.startswith("I could not find relevant information")

                if answerable:
                    # A refusal is never a correct answer to an answerable question
                    record["correct"] = not gate_refusal and any(
                        norm(fragment) in norm(answer) for fragment in item["answer_any"]
                    )
                    record["citation_hit"] = bool(relevant & set(sources))
                    record["citation_precision"] = (
                        len(relevant & set(sources)) / len(sources) if sources else 0.0
                    )
                    if not abstained:
                        record["faith"] = faithfulness(answer, context)
                else:
                    record["correct"] = abstained

                answer_rows.append(record)
                mark = "ok " if record["correct"] else "BAD"
                print(f"  [{mark}] {seconds:5.1f}s  {question}", flush=True)

    return retrieval_rows, answer_rows, contract_ids, chunk_counts


def summarise_retrieval(rows):
    answerable = [r for r in rows if r["answerable"] and "mapping_error" not in r]
    out = {
        "questions": len(answerable),
        "mapping_errors": [r["q"] for r in rows if "mapping_error" in r],
    }

    for name, key in (("hybrid", "hybrid_top"), ("vector_only", "vector_top")):
        precision = {k: [] for k in KS}
        norm_precision = {k: [] for k in KS}
        hit = {k: [] for k in KS}
        recall = {k: [] for k in KS}
        rr = []

        for r in answerable:
            rel = set(r["relevant_chunks"])
            ranked = r[key]

            for k in KS:
                found = len(rel & set(ranked[:k]))
                precision[k].append(found / k)
                norm_precision[k].append(found / min(k, len(rel)))
                hit[k].append(1.0 if found else 0.0)
                recall[k].append(found / len(rel))

            first = next((i for i, c in enumerate(ranked, 1) if c in rel), None)
            rr.append(1 / first if first else 0.0)

        out[name] = {
            "precision_at_k": {k: mean(precision[k]) for k in KS},
            "normalised_precision_at_k": {k: mean(norm_precision[k]) for k in KS},
            "hit_at_k": {k: mean(hit[k]) for k in KS},
            "recall_at_k": {k: mean(recall[k]) for k in KS},
            "mrr": mean(rr),
        }

    return out


def summarise_answers(rows):
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    answered = [r for r in answerable if "faith" in r]

    return {
        "answerable_questions": len(answerable),
        "answer_correctness": mean([1.0 if r["correct"] else 0.0 for r in answerable]),
        "citation_hit_rate": mean([1.0 if r["citation_hit"] else 0.0 for r in answerable]),
        "citation_precision": mean([r["citation_precision"] for r in answerable]),
        "unanswerable_questions": len(unanswerable),
        "correct_abstention_rate": mean([1.0 if r["correct"] else 0.0 for r in unanswerable]),
        "hallucination_rate_on_unanswerable": mean(
            [0.0 if r["correct"] else 1.0 for r in unanswerable]
        ),
        "faithfulness_sentence_score": mean([r["faith"]["score"] for r in answered]),
        "fully_faithful_answers": mean(
            [1.0 if r["faith"]["fully_faithful"] else 0.0 for r in answered]
        ),
        "answers_with_ungrounded_numbers": sum(
            1 for r in answered if r["faith"]["ungrounded_numbers"]
        ),
        "latency_seconds": {
            "mean": round(st.mean(r["seconds"] for r in rows), 2),
            "median": round(st.median(r["seconds"] for r in rows), 2),
            "max": round(max(r["seconds"] for r in rows), 2),
        },
    }


# ---------------------------------------------------------------------
# 3+4. risk rules and classifier on hand-labeled clauses
# ---------------------------------------------------------------------

def eval_risk(risk_set):
    from clausenexa_ml.risk_detector import detect_risk

    rows = []
    for item in risk_set["clauses"]:
        result = detect_risk(item["text"], item["category"])
        rows.append({
            **item,
            "predicted": result["risk_level"],
            "score": result["risk_score"],
            "reasons": result["reasons"],
        })

    confusion = {e: Counter() for e in LEVELS}
    for r in rows:
        confusion[r["expected"]][r["predicted"]] += 1

    per_level = {}
    for level in LEVELS:
        tp = sum(1 for r in rows if r["expected"] == level and r["predicted"] == level)
        fp = sum(1 for r in rows if r["expected"] != level and r["predicted"] == level)
        fn = sum(1 for r in rows if r["expected"] == level and r["predicted"] != level)
        p, rc, f = prf(tp, fp, fn)
        per_level[level] = {
            "precision": p, "recall": rc, "f1": f,
            "support": sum(1 for r in rows if r["expected"] == level),
        }

    # The product claim: flag clauses that need attention (Medium or High)
    def attention(level):
        return level in ("Medium", "High")

    tp = sum(1 for r in rows if attention(r["expected"]) and attention(r["predicted"]))
    fp = sum(1 for r in rows if not attention(r["expected"]) and attention(r["predicted"]))
    fn = sum(1 for r in rows if attention(r["expected"]) and not attention(r["predicted"]))
    p, rc, f = prf(tp, fp, fn)

    index = {lv: i for i, lv in enumerate(LEVELS)}
    exact = [r["expected"] == r["predicted"] for r in rows]
    within_one = [abs(index[r["expected"]] - index.get(r["predicted"], 9)) <= 1 for r in rows]

    by_category = defaultdict(list)
    for r in rows:
        by_category[r["category"]].append(r["expected"] == r["predicted"])

    return {
        "clauses": len(rows),
        "accuracy": mean([1.0 if e else 0.0 for e in exact]),
        "within_one_level": mean([1.0 if w else 0.0 for w in within_one]),
        "macro_f1": mean([v["f1"] for v in per_level.values()]),
        "per_level": per_level,
        "attention_flag": {"precision": p, "recall": rc, "f1": f},
        "confusion": {e: dict(c) for e, c in confusion.items()},
        "accuracy_by_category": {c: mean([1.0 if v else 0.0 for v in vals]) for c, vals in by_category.items()},
        "misses": [
            {k: r[k] for k in ("category", "expected", "predicted", "score", "reasons", "text")}
            for r in rows if r["expected"] != r["predicted"]
        ],
    }


def eval_classifier(risk_set):
    from clausenexa_ml.classifier import predict_clause_categories

    items = risk_set["clauses"]
    predictions = predict_clause_categories([i["text"] for i in items], batch_size=16)

    rows = [
        {"text": i["text"], "expected": i["category"], "predicted": cat, "confidence": round(conf, 3)}
        for i, (cat, conf) in zip(items, predictions)
    ]
    correct = [r["expected"] == r["predicted"] for r in rows]

    return {
        "clauses": len(rows),
        "accuracy": mean([1.0 if c else 0.0 for c in correct]),
        "mean_confidence": mean([r["confidence"] for r in rows]),
        "errors": [r for r in rows if r["expected"] != r["predicted"]],
    }


# ---------------------------------------------------------------------
# report
# ---------------------------------------------------------------------

def pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def render_markdown(res) -> str:
    L = []
    add = L.append
    add("# ClauseNexa evaluation")
    add("")
    add(f"_Generated by `tests/eval/run_eval.py` on {time.strftime('%Y-%m-%d')}. "
        "Re-run it to refresh these numbers._")
    add("")
    add("## What was measured")
    add("")
    add("| Proposal metric | Component | Section |")
    add("|---|---|---|")
    add("| Precision@K | Retrieval | 1 |")
    add("| Answer faithfulness | RAG generation | 2 |")
    add("| Citation correctness | RAG sources | 2 |")
    add("| Precision / recall / F1 | Risk rules | 3 |")
    add("| Precision / recall / F1 | Clause classifier | 4 (agreement) and ML_HANDOFF.md (test set) |")
    add("")
    add("**Test data.** 4 fictional contracts (services, NDA, employment, lease) run through the real "
        "upload, process and ask API. "
        f"Chunks per contract: {res['chunk_counts']}. Questions: "
        f"{res['retrieval']['questions']} answerable and {res['answers']['unanswerable_questions'] if res.get('answers') else 'n/a'} "
        "unanswerable, written by hand with a gold passage per question (`tests/eval/qa_set.json`).")
    add("")

    r = res["retrieval"]
    add("## 1. Retrieval")
    add("")
    add("Relevant chunk = a chunk containing the gold clause text. Contracts are short "
        f"(chunks per contract: {min(res['chunk_counts'].values())}-{max(res['chunk_counts'].values())}), so "
        "**Precision@K is capped low** (a question usually needs one clause; the _normalised_ columns divide by "
        "min(K, relevant chunks)) and **Hit@3/Hit@5 are trivially 100% on contracts with 5 or fewer chunks**. "
        "Hit@1 and MRR are the informative numbers; the second table repeats them for the only contract with more than 5 chunks.")
    add("")
    add("| Method | P@1 | P@3 | P@5 | Norm. P@3 | Norm. P@5 | Hit@1 | Hit@3 | Hit@5 | MRR |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for name, label in (("vector_only", "Vector only"), ("hybrid", "Hybrid (current)")):
        m = r[name]
        add(f"| {label} | {pct(m['precision_at_k'][1])} | {pct(m['precision_at_k'][3])} | {pct(m['precision_at_k'][5])} | "
            f"{pct(m['normalised_precision_at_k'][3])} | {pct(m['normalised_precision_at_k'][5])} | "
            f"{pct(m['hit_at_k'][1])} | {pct(m['hit_at_k'][3])} | {pct(m['hit_at_k'][5])} | {m['mrr']:.3f} |")
    big = res["retrieval_large"]
    if big["questions"]:
        add("")
        add(f"Only contracts with more than 5 chunks ({big['questions']} questions):")
        add("")
        add("| Method | P@1 | P@3 | Hit@1 | Hit@3 | Hit@5 | MRR |")
        add("|---|---|---|---|---|---|---|")
        for name, label in (("vector_only", "Vector only"), ("hybrid", "Hybrid (current)")):
            m = big[name]
            add(f"| {label} | {pct(m['precision_at_k'][1])} | {pct(m['precision_at_k'][3])} | "
                f"{pct(m['hit_at_k'][1])} | {pct(m['hit_at_k'][3])} | {pct(m['hit_at_k'][5])} | {m['mrr']:.3f} |")
    if r["mapping_errors"]:
        add("")
        add(f"Gold text not found in any chunk (test-data errors, excluded): {r['mapping_errors']}")
    add("")

    a = res.get("answers")
    if a:
        add("## 2. RAG answers")
        add("")
        add("| Metric | Value |")
        add("|---|---|")
        add(f"| Answer correctness (answerable questions) | {pct(a['answer_correctness'])} |")
        add(f"| Citation hit rate (a cited chunk contains the answer) | {pct(a['citation_hit_rate'])} |")
        add(f"| Citation precision (cited chunks that are relevant) | {pct(a['citation_precision'])} |")
        add(f"| Correct abstention on unanswerable questions | {pct(a['correct_abstention_rate'])} |")
        add(f"| Hallucination rate on unanswerable questions | {pct(a['hallucination_rate_on_unanswerable'])} |")
        add(f"| Faithfulness, sentence-level (lexical proxy) | {pct(a['faithfulness_sentence_score'])} |")
        add(f"| Fully faithful answers | {pct(a['fully_faithful_answers'])} |")
        add(f"| Answers containing a number not in the context | {a['answers_with_ungrounded_numbers']} |")
        add(f"| Latency, mean / median / max | {a['latency_seconds']['mean']}s / {a['latency_seconds']['median']}s / {a['latency_seconds']['max']}s |")
        add("")
        add("Faithfulness here is a **lexical proxy**: a sentence counts as supported when at least 70% of its content "
            "words appear in the cited chunks, and every number must appear there. It does not check logic or negation, "
            "so treat it as an upper bound and spot-check failures. Citation precision is low by design when 5 chunks are returned "
            "for a one-clause question.")
        add("")
        wrong = [x for x in res["answer_rows"] if not x["correct"]]
        if wrong:
            add("Answers marked wrong:")
            add("")
            for x in wrong:
                add(f"- **{x['contract']}** - {x['q']}  \n  `{x['answer'][:200]!r}`")
            add("")

    k = res["risk"]
    add("## 3. Risk rules (72 hand-labeled clauses)")
    add("")
    add(f"Accuracy **{pct(k['accuracy'])}**, within one level **{pct(k['within_one_level'])}**, macro F1 **{k['macro_f1']}**. "
        "Labels were written from the documented scoring rubric and **should be reviewed by the ML owner** before being quoted as ground truth.")
    add("")
    add("| Level | Precision | Recall | F1 | Support |")
    add("|---|---|---|---|---|")
    for level in LEVELS:
        m = k["per_level"][level]
        add(f"| {level} | {pct(m['precision'])} | {pct(m['recall'])} | {pct(m['f1'])} | {m['support']} |")
    af = k["attention_flag"]
    add("")
    add(f"**Attention flag** (Medium or High vs Low, the product's core claim): precision {pct(af['precision'])}, "
        f"recall {pct(af['recall'])}, F1 {pct(af['f1'])}.")
    add("")
    add("Confusion (rows = expected, columns = predicted):")
    add("")
    add("| | Low | Medium | High |")
    add("|---|---|---|---|")
    for e in LEVELS:
        c = k["confusion"][e]
        add(f"| {e} | {c.get('Low', 0)} | {c.get('Medium', 0)} | {c.get('High', 0)} |")
    add("")
    add("Accuracy by category: " + ", ".join(f"{c} {pct(v)}" for c, v in k["accuracy_by_category"].items()))
    add("")
    if k["misses"]:
        add(f"### Misclassified clauses ({len(k['misses'])})")
        add("")
        for m in k["misses"]:
            add(f"- **{m['category']}**: expected {m['expected']}, got {m['predicted']} (score {m['score']}) - "
                f"{m['text'][:110]}  \n  reasons: {m['reasons']}")
        add("")

    c = res.get("classifier")
    if c:
        add("## 4. Clause classifier on the same clauses")
        add("")
        add(f"Legal-BERT agreed with the intended category on **{pct(c['accuracy'])}** of {c['clauses']} short hand-written clauses "
            f"(mean confidence {c['mean_confidence']}). The proper held-out test results (7-class macro F1 0.9812, accuracy 0.9884) "
            "are in `docs/ML_HANDOFF.md`; this is only a sanity check on unseen wording.")
        add("")
        for e in c["errors"]:
            add(f"- expected {e['expected']}, predicted {e['predicted']} ({e['confidence']}) - {e['text'][:100]}")
        add("")

    add("## Limitations")
    add("")
    add("- Four small fictional contracts and about 45 questions: a smoke-level benchmark, not a statistically strong one.")
    add("- Gold labels were written by one person (the assistant) and should be reviewed by the team.")
    add("- Faithfulness is lexical, not an LLM or NLI judge.")
    add("- The risk rules are keyword rules, so wording they were never given (see misses) is the main failure mode.")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------
# main
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--skip-ask", action="store_true", help="skip LLM answers")
    parser.add_argument("--keep", action="store_true", help="keep test contracts in Supabase")
    args = parser.parse_args()

    from supabase import create_client

    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    qa_set = json.load(open(HERE / "qa_set.json", encoding="utf-8"))
    risk_set = json.load(open(HERE / "risk_set.json", encoding="utf-8"))

    requests.get(f"{args.base_url}/health", timeout=10).raise_for_status()

    contract_ids = []
    try:
        retrieval_rows, answer_rows, contract_ids, chunk_counts = eval_rag(
            args.base_url, not args.skip_ask, supabase, qa_set
        )
    finally:
        if not args.keep:
            for contract_id in contract_ids:
                try:
                    requests.delete(f"{args.base_url}/contracts/{contract_id}", timeout=60)
                except Exception as exc:
                    print("cleanup failed for", contract_id, exc)

    results = {
        "chunk_counts": chunk_counts,
        "retrieval": summarise_retrieval(retrieval_rows),
        "retrieval_large": summarise_retrieval(
            [r for r in retrieval_rows if chunk_counts[r["contract"]] > 5]
        ),
        "retrieval_rows": retrieval_rows,
        "risk": eval_risk(risk_set),
        "classifier": eval_classifier(risk_set),
    }
    if answer_rows:
        results["answers"] = summarise_answers(answer_rows)
        results["answer_rows"] = answer_rows

    (HERE / "results.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    (ROOT / "docs" / "EVALUATION.md").write_text(render_markdown(results), encoding="utf-8")
    print("\nwrote tests/eval/results.json and docs/EVALUATION.md")


if __name__ == "__main__":
    main()
