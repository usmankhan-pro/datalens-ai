"""Rule-based domain detection from DataFrame column names."""

from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "Finance": [
        "revenue", "profit", "ebitda", "margin", "cost", "expense", "tax", "invoice",
        "balance", "ledger", "asset", "liability", "transaction", "amount", "currency",
        "payment", "dividend", "interest", "debt", "budget", "price",
    ],
    "Healthcare": [
        "patient", "diagnosis", "doctor", "hospital", "clinic", "treatment", "symptom",
        "blood", "dosage", "medical", "health", "prescription", "lab", "glucose", "bmi",
        "cholesterol", "disease", "admission", "discharge", "physician",
    ],
    "E-Commerce": [
        "order", "cart", "sku", "product", "shipping", "delivery", "checkout", "discount",
        "coupon", "inventory", "customer", "buyer", "unit_price", "quantity", "store",
        "fulfillment", "return", "refund", "catalog",
    ],
    "Marketing": [
        "campaign", "lead", "click", "ctr", "impression", "conversion", "spend", "ad",
        "cpa", "cpc", "channel", "traffic", "visitor", "bounce", "funnel", "utm",
        "subscriber", "newsletter", "reach",
    ],
    "HR & Workforce": [
        "employee", "salary", "bonus", "department", "hire_date", "termination",
        "job_title", "tenure", "payroll", "performance_rating", "headcount", "manager",
        "attendance", "leave", "attrition",
    ],
    "SaaS & Tech": [
        "mrr", "arr", "churn", "subscription", "plan", "trial", "renewal", "tier",
        "seats", "active_users", "dau", "mau", "tenant", "workspace", "api_calls",
        "feature_flag", "license",
    ],
}


def detect_domain(columns: Sequence[str]) -> Tuple[str, float]:
    """
    Detect dataset business domain based on column header keywords.

    Args:
        columns: Sequence of column names.

    Returns:
        Tuple of (domain_name, confidence_score_between_0_and_1).
    """
    if not columns:
        return "General", 0.0

    normalized_cols = [re.sub(r"[^a-z0-9]", "", str(c).lower()) for c in columns]
    scores: Dict[str, int] = {domain: 0 for domain in DOMAIN_KEYWORDS}

    for col in normalized_cols:
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                clean_kw = kw.replace("_", "")
                if clean_kw in col:
                    scores[domain] += 1
                    break

    best_domain = "General"
    best_score = 0
    total_matches = sum(scores.values())

    for domain, score in scores.items():
        if score > best_score:
            best_score = score
            best_domain = domain

    if best_score == 0:
        return "General", 0.0

    # Confidence calculation: ratio of matched columns to total columns, bounded [0.2, 0.95]
    confidence = min(0.95, max(0.2, (best_score / len(columns)) * 1.5))
    return best_domain, round(confidence, 2)
