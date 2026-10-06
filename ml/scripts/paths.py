"""
Central file locations and shared constants for the ClauseNexa ML scripts.

Every path is built relative to the repository root, so the scripts run on any
machine (Windows, Mac, Google Colab) without editing hardcoded C:\\Users\\...
paths. Import from here instead of typing paths inside each script.
"""

from pathlib import Path


# -------------------------------------------------
# 1. FOLDERS
# -------------------------------------------------

# This file lives at ml/scripts/paths.py -> parents[2] is the repository root
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
MODELS_DIR = REPO_ROOT / "ml" / "models"


# -------------------------------------------------
# 2. DATA FILES
# -------------------------------------------------

# Full LEDGAR corpus: one JSON record per line with "provision", "label", "source"
LEDGAR_JSONL = DATA_RAW / "LEDGAR_2016-2019_clean.jsonl"

# Every LEDGAR label with its frequency (written by 01_build_ledgar_dataset.py)
LEDGAR_LABELS_TXT = DATA_PROCESSED / "LEDGAR_all_labels.txt"

# LEDGAR mapped to the 6 ClauseNexa categories, still including multi-label clauses
LEDGAR_FINAL_CSV = DATA_PROCESSED / "ClauseNexa_LEDGAR_Final.csv"

# Final single-label training dataset used by BOTH classifiers
CLEAN_SINGLE_LABEL_CSV = DATA_PROCESSED / "ClauseNexa_LEDGAR_Clean_SingleLabel.csv"

# Misclassified test clauses from the Logistic Regression baseline (error analysis)
LOGREG_ERRORS_CSV = DATA_PROCESSED / "ClauseNexa_LogReg_V2_Errors.csv"


# -------------------------------------------------
# 3. MODEL FOLDERS
# -------------------------------------------------

LOGREG_DIR = MODELS_DIR / "logistic_regression"
LEGALBERT_DIR = MODELS_DIR / "legalbert_classifier"

# Intermediate Hugging Face Trainer checkpoints (large, git-ignored)
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints"


# -------------------------------------------------
# 4. SHARED CONSTANTS
# -------------------------------------------------

# The 6 ClauseNexa categories, in alphabetical order. This order matches
# sklearn's LabelEncoder, so index i here == label id i in the Legal-BERT model.
CATEGORIES = [
    "Confidentiality",
    "Governing Law",
    "Liability",
    "Non-Compete",
    "Payment",
    "Termination",
]

# One seed everywhere so splits and results are reproducible
RANDOM_STATE = 42
