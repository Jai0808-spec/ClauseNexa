"""
ClauseNexa ML layer: clause splitting, Legal-BERT (7-class) classification and
rule-based risk detection.

Backend usage:
    from clausenexa_ml import analyze_contract
    report = analyze_contract(contract_text)   # JSON-ready dict
"""

from .clause_splitter import split_contract_text
from .contract_analyzer import analyze_clause, analyze_contract, analyze_multiple_clauses
from .risk_detector import detect_risk

__all__ = [
    "analyze_contract",
    "analyze_multiple_clauses",
    "analyze_clause",
    "split_contract_text",
    "detect_risk",
]
