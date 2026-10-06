"""
Step 4 — Fine-tune Legal-BERT for clause classification (final classifier).

Model: nlpaueb/legal-bert-base-uncased (BERT pre-trained on legal text),
fine-tuned to predict one of the 6 ClauseNexa categories.

Pipeline:
  1. Load the cleaned single-label dataset and encode labels 0-5 (alphabetical).
  2. Grouped 70/15/15 train/validation/test split by source contract
     (no contract appears in more than one split).
  3. (Optional, --analyse-lengths) token-length analysis that justified
     max_length=384: median 94, p95 403 tokens; only 5.84% of clauses exceed
     384 tokens, while 512 would cost ~1.8x more memory/compute per example.
  4. Tokenize with max_length=384 (longer clauses are truncated).
  5. Train with Hugging Face Trainer; the best epoch is chosen by validation
     Macro F1 (Macro F1 treats small classes like Non-Compete as equally important).
  6. Evaluate ONCE on the untouched test set.
  7. Save model + tokenizer + label_mapping.json to ml/models/legalbert_classifier/.

Final results (Colab, T4 GPU, 3 epochs):
  - Validation Macro F1 by epoch: 0.986645 -> 0.988861 -> 0.989134
  - Test Accuracy 0.994282, Macro F1 0.988606, Weighted F1 0.994277

Converted from: legalbert_classifier.ipynb. NOTE: that local notebook only
contains a CPU smoke test (1,000 samples, 1 epoch, batch 2 — reproduce it with
--smoke-test). The full training was run in Google Colab; the full-run settings
below are reconstructed from the recorded hyper-parameters (3 epochs, batch 8,
lr 2e-5, weight decay 0.01, fp16, best model by Macro F1).

Run (GPU strongly recommended, e.g. Colab T4):
    python ml/scripts/04_train_legalbert.py
    python ml/scripts/04_train_legalbert.py --smoke-test        # quick CPU check
    python ml/scripts/04_train_legalbert.py --analyse-lengths   # token stats only
"""

import argparse
import json
import os

import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupShuffleSplit
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from paths import (
    CATEGORIES,
    CHECKPOINTS_DIR,
    CLEAN_SINGLE_LABEL_CSV,
    LEGALBERT_DIR,
    RANDOM_STATE,
)


BASE_MODEL = "nlpaueb/legal-bert-base-uncased"
MAX_LENGTH = 384

# Label ids follow alphabetical order (same as sklearn's LabelEncoder)
ID2LABEL = dict(enumerate(CATEGORIES))
LABEL2ID = {label: idx for idx, label in ID2LABEL.items()}


# -------------------------------------------------
# 1. DATA
# -------------------------------------------------

def load_data(path):
    df = pd.read_csv(path)
    df["label_id"] = df["clause_category"].map(LABEL2ID)

    # Every category in the CSV must be one of the 6 known categories
    assert df["label_id"].notna().all(), "Unknown category found in dataset"

    print("Dataset shape:", df.shape)
    print(df["clause_category"].value_counts())
    return df


def grouped_train_val_test_split(df):
    """
    70% train / 15% validation / 15% test, grouped by source contract.

    Done in two steps: first 70/30, then the 30% is split 50/50.
    The same random_state reproduces the exact split used for the reported results.
    """

    # Step 1: 70% train, 30% temporary
    gss_1 = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=RANDOM_STATE)
    train_idx, temp_idx = next(gss_1.split(df, groups=df["source"]))

    train_df = df.iloc[train_idx].copy()
    temp_df = df.iloc[temp_idx].copy()

    # Step 2: temporary -> 15% validation + 15% test
    gss_2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=RANDOM_STATE)
    val_idx, test_idx = next(gss_2.split(temp_df, groups=temp_df["source"]))

    val_df = temp_df.iloc[val_idx].copy()
    test_df = temp_df.iloc[test_idx].copy()

    # Report sizes and confirm there is no contract leakage between splits
    print("\nTrain / Validation / Test samples:", len(train_df), len(val_df), len(test_df))

    train_s, val_s, test_s = (set(d["source"]) for d in (train_df, val_df, test_df))
    print("Train-Validation overlap:", len(train_s & val_s))
    print("Train-Test overlap:", len(train_s & test_s))
    print("Validation-Test overlap:", len(val_s & test_s))

    return train_df, val_df, test_df


def analyse_token_lengths(df, tokenizer):
    """Print token-length statistics used to choose MAX_LENGTH."""

    lengths = np.array([
        len(tokenizer(text, truncation=False, add_special_tokens=True)["input_ids"])
        for text in df["clause_text"]
    ])

    print("\nToken length statistics over", len(lengths), "clauses:")
    print("Mean:", round(lengths.mean(), 2))
    print("Median:", np.median(lengths))
    for p in (90, 95, 99):
        print(f"{p}th percentile:", np.percentile(lengths, p))
    print("Maximum:", lengths.max())

    for limit in (128, 256, 384, 512):
        count = int((lengths > limit).sum())
        print(f"Above {limit} tokens: {count} ({count / len(lengths) * 100:.2f}%)")


def to_tokenized_dataset(df, tokenizer):
    """Convert a DataFrame into a tokenized Hugging Face Dataset for the Trainer."""

    dataset = Dataset.from_pandas(df[["clause_text", "label_id"]], preserve_index=False)

    def tokenize(batch):
        return tokenizer(
            batch["clause_text"],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
        )

    dataset = dataset.map(tokenize, batched=True)

    # The Trainer expects the target column to be called "labels",
    # and the raw text is no longer needed after tokenization
    dataset = dataset.rename_column("label_id", "labels")
    return dataset.remove_columns(["clause_text"])


# -------------------------------------------------
# 2. TRAINING
# -------------------------------------------------

def compute_metrics(eval_pred):
    """Metrics reported by the Trainer after every evaluation."""

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)

    return {
        "accuracy": accuracy_score(labels, predictions),
        "macro_f1": f1_score(labels, predictions, average="macro"),
        "weighted_f1": f1_score(labels, predictions, average="weighted"),
    }


def make_training_args(smoke_test):
    """
    Full run = the Colab T4 configuration.
    Smoke test = the small CPU configuration from the local notebook, used only
    to check that the pipeline runs end to end.
    """

    common = dict(
        output_dir=str(CHECKPOINTS_DIR),
        learning_rate=2e-5,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,       # keep the epoch with the best...
        metric_for_best_model="macro_f1",  # ...validation Macro F1
        greater_is_better=True,
        logging_strategy="steps",
        logging_steps=50,
        save_total_limit=1,                # keep disk usage down (checkpoints are ~1.3 GB)
        seed=RANDOM_STATE,
        report_to="none",
    )

    if smoke_test:
        return TrainingArguments(
            num_train_epochs=1,
            per_device_train_batch_size=2,
            per_device_eval_batch_size=2,
            **common,
        )

    return TrainingArguments(
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        fp16=torch.cuda.is_available(),  # mixed precision needs a GPU
        **common,
    )


# -------------------------------------------------
# 3. TEST EVALUATION AND SAVING
# -------------------------------------------------

def evaluate_on_test(trainer, test_dataset):
    """Single, final evaluation on the untouched test set."""

    output = trainer.predict(test_dataset)
    y_true = output.label_ids
    y_pred = np.argmax(output.predictions, axis=-1)

    print("\nFINAL TEST RESULTS")
    print("Accuracy:", round(accuracy_score(y_true, y_pred), 6))
    print("Macro F1:", round(f1_score(y_true, y_pred, average="macro"), 6))
    print("Weighted F1:", round(f1_score(y_true, y_pred, average="weighted"), 6))

    print("\nClassification Report:\n")
    print(classification_report(y_true, y_pred, target_names=CATEGORIES, digits=4))


def save_model(trainer, tokenizer, output_dir):
    """Save everything needed for inference: weights, config, tokenizer, labels."""

    os.makedirs(output_dir, exist_ok=True)

    trainer.save_model(output_dir)          # model.safetensors + config.json (with id2label)
    tokenizer.save_pretrained(output_dir)   # tokenizer.json + tokenizer_config.json

    with open(os.path.join(output_dir, "label_mapping.json"), "w", encoding="utf-8") as f:
        json.dump({str(i): label for i, label in ID2LABEL.items()}, f, indent=4)

    print("\nModel, tokenizer and label mapping saved to:", output_dir)


# -------------------------------------------------
# 4. MAIN
# -------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--data", default=CLEAN_SINGLE_LABEL_CSV, help="training dataset CSV")
    parser.add_argument("--output-dir", default=LEGALBERT_DIR, help="where to save the trained model")
    parser.add_argument("--smoke-test", action="store_true",
                        help="1 epoch on 1,000/300 samples to test the pipeline on CPU")
    parser.add_argument("--analyse-lengths", action="store_true",
                        help="only print token-length statistics, then exit")
    args = parser.parse_args()

    df = load_data(args.data)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    if args.analyse_lengths:
        analyse_token_lengths(df, tokenizer)
        return

    # 1. Split and tokenize
    train_df, val_df, test_df = grouped_train_val_test_split(df)

    train_ds = to_tokenized_dataset(train_df, tokenizer)
    val_ds = to_tokenized_dataset(val_df, tokenizer)
    test_ds = to_tokenized_dataset(test_df, tokenizer)

    if args.smoke_test:
        train_ds = train_ds.shuffle(seed=RANDOM_STATE).select(range(1000))
        val_ds = val_ds.shuffle(seed=RANDOM_STATE).select(range(300))

    # 2. Load Legal-BERT with a fresh 6-class classification head.
    #    id2label/label2id are stored in config.json, so the saved model returns
    #    category names instead of LABEL_0..LABEL_5.
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(CATEGORIES),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # 3. Train
    trainer = Trainer(
        model=model,
        args=make_training_args(args.smoke_test),
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
    )
    trainer.train()

    # 4. Test + save (the smoke-test model is not good enough to keep)
    evaluate_on_test(trainer, test_ds)

    if not args.smoke_test:
        save_model(trainer, tokenizer, args.output_dir)


if __name__ == "__main__":
    main()
