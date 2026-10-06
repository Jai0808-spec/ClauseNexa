"""
Step 3 — Train and evaluate the TF-IDF + Logistic Regression baseline.

This is the classical-ML baseline that Legal-BERT is compared against.

Pipeline:
  1. Grouped 80/20 train/test split by source contract (GroupShuffleSplit).
     Clauses from the same contract often share wording; a plain random split
     would leak that wording into the test set and inflate the scores.
  2. TF-IDF features (unigrams + bigrams, 20k features), fitted on TRAIN only.
  3. 5-fold StratifiedGroupKFold cross-validation on the training set
     (stratified = keeps class balance, grouped = still no contract leakage).
  4. Final model trained on the full 80%, evaluated once on the untouched 20%.
  5. Misclassified test clauses saved to CSV for error analysis.
  6. Vectorizer + model saved with joblib.

Results on the cleaned single-label dataset:
  - Train 33,854 / Test 8,505, source overlap 0
  - CV Macro F1 0.9781
  - Test Accuracy 0.9893, Macro F1 0.9816, Weighted F1 0.9893

Converted from: Logistic Regression baseline.ipynb (cells 4-8 on the uncleaned
data, then 12-18 on the cleaned data). To reproduce the earlier uncleaned run,
pass --data data/processed/ClauseNexa_LEDGAR_Final.csv.

Run: python ml/scripts/03_train_logistic_regression.py [--skip-cv]
"""

import argparse
import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold, cross_val_score

from paths import CLEAN_SINGLE_LABEL_CSV, LOGREG_DIR, LOGREG_ERRORS_CSV, RANDOM_STATE


TFIDF_FILENAME = "tfidf_vectorizer_v2_clean.joblib"
MODEL_FILENAME = "logistic_regression_v2_clean.joblib"


# -------------------------------------------------
# 1. MODEL DEFINITIONS
# -------------------------------------------------

def make_vectorizer():
    """TF-IDF over unigrams + bigrams; bigrams capture phrases like 'governing law'."""

    return TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        max_features=20000,
    )


def make_classifier():
    """
    class_weight="balanced" up-weights rare classes (Non-Compete, Liability),
    so the model is not dominated by Governing Law (~48% of the data).
    """

    return LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )


# -------------------------------------------------
# 2. GROUPED TRAIN / TEST SPLIT
# -------------------------------------------------

def grouped_split(df, test_size=0.20):
    """Split so that every source contract lands entirely in train OR test."""

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=RANDOM_STATE)

    train_idx, test_idx = next(
        gss.split(df["clause_text"], df["clause_category"], groups=df["source"])
    )

    return df.iloc[train_idx], df.iloc[test_idx]


def report_split(train_df, test_df):
    """Print split sizes, contract counts, leakage check and class balance."""

    print("\nTraining samples:", len(train_df))
    print("Testing samples:", len(test_df))

    print("\nTraining contracts:", train_df["source"].nunique())
    print("Testing contracts:", test_df["source"].nunique())

    # Must be 0: no contract may appear in both sets
    overlap = set(train_df["source"]) & set(test_df["source"])
    print("\nSource overlap between train and test:", len(overlap))

    print("\nTraining class percentages:")
    print((train_df["clause_category"].value_counts(normalize=True) * 100).round(2))
    print("\nTesting class percentages:")
    print((test_df["clause_category"].value_counts(normalize=True) * 100).round(2))


# -------------------------------------------------
# 3. EVALUATION
# -------------------------------------------------

def cross_validate(X_train_tfidf, y_train, groups_train):
    """Grouped, stratified 5-fold CV on the training set, scored by Macro F1."""

    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    scores = cross_val_score(
        make_classifier(),
        X_train_tfidf,
        y_train,
        groups=groups_train,
        cv=cv,
        scoring="f1_macro",
    )

    print("\nGrouped 5-Fold Macro F1 scores:", scores.round(4))
    print("Mean CV Macro F1:", round(scores.mean(), 4))
    print("Std CV Macro F1:", round(scores.std(), 4))


def evaluate(model, y_test, y_pred):
    """Print accuracy, macro/weighted F1, per-class report and confusion matrix."""

    print("\nFINAL TEST RESULTS")
    print("Test Accuracy:", round(accuracy_score(y_test, y_pred), 4))
    print("Macro F1:", round(f1_score(y_test, y_pred, average="macro"), 4))
    print("Weighted F1:", round(f1_score(y_test, y_pred, average="weighted"), 4))

    print("\nClassification Report:\n")
    print(classification_report(y_test, y_pred, digits=4))

    print("Classes:", list(model.classes_))
    print("\nConfusion Matrix (rows = true, columns = predicted):")
    print(confusion_matrix(y_test, y_pred, labels=model.classes_))


def save_errors(test_df, y_pred, output_path):
    """Save misclassified test clauses and print the most common confusions."""

    results = pd.DataFrame({
        "clause_text": test_df["clause_text"].values,
        "true_label": test_df["clause_category"].values,
        "predicted_label": y_pred,
    })

    errors = results[results["true_label"] != results["predicted_label"]].copy()

    print("\nTotal test samples:", len(results))
    print("Total misclassified:", len(errors))

    print("\nError combinations:")
    print(
        errors.groupby(["true_label", "predicted_label"])
        .size()
        .sort_values(ascending=False)
    )

    # Non-Compete false positives were the main weakness of the baseline
    # (mostly Confidentiality clauses that also restrict employee behaviour)
    noncompete_fp = errors[
        (errors["predicted_label"] == "Non-Compete")
        & (errors["true_label"] != "Non-Compete")
    ]
    print("\nNon-Compete false positives:", len(noncompete_fp))

    errors.to_csv(output_path, index=False, encoding="utf-8-sig")
    print("Error file saved to:", output_path)


# -------------------------------------------------
# 4. SAVE / LOAD CHECK
# -------------------------------------------------

def save_models(vectorizer, model, model_dir):
    os.makedirs(model_dir, exist_ok=True)

    tfidf_path = os.path.join(model_dir, TFIDF_FILENAME)
    model_path = os.path.join(model_dir, MODEL_FILENAME)

    joblib.dump(vectorizer, tfidf_path)
    joblib.dump(model, model_path)

    print("\nTF-IDF saved to:", tfidf_path)
    print("Logistic Regression saved to:", model_path)
    return tfidf_path, model_path


def sanity_check(tfidf_path, model_path):
    """Reload the saved files and classify one example clause."""

    loaded_tfidf = joblib.load(tfidf_path)
    loaded_model = joblib.load(model_path)

    sample_clause = [
        "The employee shall not disclose any confidential or proprietary "
        "information of the Company to any third party."
    ]

    probabilities = loaded_model.predict_proba(loaded_tfidf.transform(sample_clause))[0]

    print("\nSanity check — predicted:", loaded_model.classes_[probabilities.argmax()])
    for label, prob in zip(loaded_model.classes_, probabilities):
        print(f"  {label}: {prob:.4f}")


# -------------------------------------------------
# 5. MAIN
# -------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--data", default=CLEAN_SINGLE_LABEL_CSV,
                        help="training dataset CSV")
    parser.add_argument("--errors-output", default=LOGREG_ERRORS_CSV,
                        help="where to save misclassified test clauses")
    parser.add_argument("--model-dir", default=LOGREG_DIR,
                        help="folder for the saved vectorizer and model")
    parser.add_argument("--skip-cv", action="store_true",
                        help="skip 5-fold cross-validation (faster)")
    args = parser.parse_args()

    # 1. Load data
    df = pd.read_csv(args.data)
    print("Dataset shape:", df.shape)
    print("Unique source contracts:", df["source"].nunique())

    # 2. Grouped split
    train_df, test_df = grouped_split(df)
    report_split(train_df, test_df)

    # 3. TF-IDF — fit on training data only, then reuse the same vocabulary for test
    vectorizer = make_vectorizer()
    X_train_tfidf = vectorizer.fit_transform(train_df["clause_text"])
    X_test_tfidf = vectorizer.transform(test_df["clause_text"])
    print("\nTF-IDF shapes — train:", X_train_tfidf.shape, "test:", X_test_tfidf.shape)

    # 4. Cross-validation
    if not args.skip_cv:
        cross_validate(X_train_tfidf, train_df["clause_category"], train_df["source"])

    # 5. Final model on all training data, evaluated once on the untouched test set
    model = make_classifier()
    model.fit(X_train_tfidf, train_df["clause_category"])

    y_pred = model.predict(X_test_tfidf)
    evaluate(model, test_df["clause_category"], y_pred)

    # 6. Error analysis + save
    save_errors(test_df, y_pred, args.errors_output)
    tfidf_path, model_path = save_models(vectorizer, model, args.model_dir)
    sanity_check(tfidf_path, model_path)


if __name__ == "__main__":
    main()
