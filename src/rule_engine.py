"""
rule_engine.py

Improved rule engine for the GL Mapping Automation project.

New features
------------
1. Enforces transaction direction:
   - transaction_type = 1 means Deposit rule
   - transaction_type = -1 means Payment rule
   - transaction_type = None means either direction

2. Supports AND / OR rule logic:
   - is_and_rule=True  -> all keywords must match
   - is_and_rule=False -> at least one keyword must match

3. Uses rule scoring instead of first-match-wins:
   - More specific rules score higher
   - Field-level matches are weighted
   - Longer keywords get a small specificity bonus

4. Adds confidence score and match reason:
   - Every mapped transaction contains confidence_score
   - Every mapped transaction contains match_reason
   - Useful for audit reports and future AI review

Author: Shruti GL Mapping Project
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


# Higher weight = stronger evidence that the rule is correct.
FIELD_WEIGHTS = {
    "Payee": 40,
    "Memo": 30,
    "Store": 20,
    "Account": 10,
}

# Minimum score needed to auto-map a transaction.
# You can tune this later after reviewing audit reports.
MINIMUM_AUTO_MATCH_SCORE = 25


@dataclass
class RuleMatchResult:
    """
    Stores the result of comparing one transaction against one rule.

    Attributes
    ----------
    matched : bool
        True if the rule is eligible for this transaction.

    score : float
        Numeric score showing match strength.

    confidence_score : float
        Score converted into a 0-100 confidence percentage.

    matched_keywords : list[str]
        Keywords from the rule that matched the transaction.

    missing_keywords : list[str]
        Keywords required by the rule but not found.

    match_reason : str
        Human-readable explanation for audit review.
    """

    matched: bool
    score: float
    confidence_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    match_reason: str


def get_transaction_direction(transaction: dict[str, Any]) -> int | None:
    """
    Determine whether a transaction is a Deposit or Payment.

    Parameters
    ----------
    transaction : dict[str, Any]
        One bank transaction row.

    Returns
    -------
    int | None
        1 for Deposit, -1 for Payment, None for invalid/ambiguous.
    """

    payment = float(transaction.get("Payment", 0) or 0)
    deposit = float(transaction.get("Deposit", 0) or 0)

    if payment > 0 and deposit == 0:
        return -1

    if deposit > 0 and payment == 0:
        return 1

    return None


def calculate_signed_amount(transaction: dict[str, Any]) -> float:
    """
    Convert bank Payment/Deposit columns into one signed Amount.

    Payment becomes negative.
    Deposit becomes positive.

    Parameters
    ----------
    transaction : dict[str, Any]
        One bank transaction row.

    Returns
    -------
    float
        Signed transaction amount.
    """

    payment = float(transaction.get("Payment", 0) or 0)
    deposit = float(transaction.get("Deposit", 0) or 0)

    if payment > 0 and deposit == 0:
        return -payment

    if deposit > 0 and payment == 0:
        return deposit

    return 0.0


def rule_direction_matches(
    transaction: dict[str, Any],
    rule: dict[str, Any],
) -> bool:
    """
    Check if a rule is allowed for the transaction direction.

    If a rule has transaction_type = 1, it should only match deposits.
    If a rule has transaction_type = -1, it should only match payments.
    If transaction_type is None, it can match either direction.
    """

    rule_transaction_type = rule.get("transaction_type")

    if rule_transaction_type is None:
        return True

    transaction_direction = get_transaction_direction(transaction)

    return transaction_direction == rule_transaction_type


def normalize_text(value: Any) -> str:
    """
    Convert any value into lowercase searchable text.
    """

    return str(value or "").lower().strip()


def keyword_matches_field(keyword: str, field_value: Any) -> bool:
    """
    Check whether a keyword exists inside a field value.

    This is case-insensitive substring matching.
    Later, this can be upgraded to regex or fuzzy matching.
    """

    keyword_text = normalize_text(keyword)
    field_text = normalize_text(field_value)

    if not keyword_text:
        return False

    return keyword_text in field_text


def score_keyword_against_transaction(
    keyword: str,
    transaction: dict[str, Any],
) -> tuple[float, list[str]]:
    """
    Score one keyword against all searchable transaction fields.

    Parameters
    ----------
    keyword : str
        Rule keyword.

    transaction : dict[str, Any]
        One bank transaction.

    Returns
    -------
    tuple[float, list[str]]
        Score and list of fields where the keyword matched.
    """

    score = 0.0
    matched_fields = []

    for field_name, field_weight in FIELD_WEIGHTS.items():
        if keyword_matches_field(keyword, transaction.get(field_name, "")):
            score += field_weight
            matched_fields.append(field_name)

    if matched_fields:
        # Longer keywords are usually more specific than short words like "Royal".
        specificity_bonus = min(len(keyword.strip()) / 10, 10)
        score += specificity_bonus

    return score, matched_fields


def evaluate_rule(
    transaction: dict[str, Any],
    rule: dict[str, Any],
) -> RuleMatchResult:
    """
    Evaluate one rule against one transaction.

    Parameters
    ----------
    transaction : dict[str, Any]
        One bank transaction.

    rule : dict[str, Any]
        One parsed bank feed rule.

    Returns
    -------
    RuleMatchResult
        Detailed match result.
    """

    if not rule_direction_matches(transaction, rule):
        return RuleMatchResult(
            matched=False,
            score=0.0,
            confidence_score=0.0,
            matched_keywords=[],
            missing_keywords=[],
            match_reason="Rejected: transaction direction does not match rule direction.",
        )

    keywords = [kw for kw in rule.get("keywords", []) if str(kw).strip()]

    if not keywords:
        return RuleMatchResult(
            matched=False,
            score=0.0,
            confidence_score=0.0,
            matched_keywords=[],
            missing_keywords=[],
            match_reason="Rejected: rule has no searchable keywords.",
        )

    is_and_rule = bool(rule.get("is_and_rule", True))
    matched_keywords = []
    missing_keywords = []
    total_score = 0.0
    reason_parts = []

    for keyword in keywords:
        keyword_score, matched_fields = score_keyword_against_transaction(
            keyword=keyword,
            transaction=transaction,
        )

        if keyword_score > 0:
            matched_keywords.append(keyword)
            total_score += keyword_score
            reason_parts.append(
                f"'{keyword}' matched in {', '.join(matched_fields)}"
            )
        else:
            missing_keywords.append(keyword)

    if is_and_rule:
        rule_matched = len(missing_keywords) == 0
    else:
        rule_matched = len(matched_keywords) > 0

    if not rule_matched:
        logic = "AND" if is_and_rule else "OR"
        return RuleMatchResult(
            matched=False,
            score=0.0,
            confidence_score=0.0,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            match_reason=(
                f"Rejected: {logic} rule requirements not satisfied. "
                f"Missing keywords: {missing_keywords}"
            ),
        )

    # AND rules are stronger because all required conditions matched.
    if is_and_rule:
        total_score *= 1.20

    # More matched keywords generally means stronger confidence.
    keyword_coverage = len(matched_keywords) / len(keywords)
    coverage_bonus = keyword_coverage * 20
    final_score = total_score + coverage_bonus

    confidence_score = min(round(final_score, 2), 100.0)

    if confidence_score < MINIMUM_AUTO_MATCH_SCORE:
        return RuleMatchResult(
            matched=False,
            score=final_score,
            confidence_score=confidence_score,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            match_reason=(
                "Rejected: score below auto-match threshold. "
                + "; ".join(reason_parts)
            ),
        )

    return RuleMatchResult(
        matched=True,
        score=final_score,
        confidence_score=confidence_score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        match_reason="; ".join(reason_parts),
    )


def find_best_rule_match(
    transaction: dict[str, Any],
    parsed_rules: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, RuleMatchResult | None, list[dict[str, Any]]]:
    """
    Find the best rule for one transaction.

    Instead of stopping at the first matching rule, this function evaluates
    all rules, scores them, and returns the highest-scoring rule.

    Returns
    -------
    tuple
        best_rule, best_match_result, candidate_matches
    """

    candidates = []

    for rule in parsed_rules:
        match_result = evaluate_rule(transaction, rule)

        if match_result.matched:
            candidates.append(
                {
                    "rule": rule,
                    "result": match_result,
                }
            )

    if not candidates:
        return None, None, []

    candidates = sorted(
        candidates,
        key=lambda item: item["result"].score,
        reverse=True,
    )

    best_candidate = candidates[0]

    return best_candidate["rule"], best_candidate["result"], candidates


def build_mapped_transaction(
    transaction: dict[str, Any],
    rule_name: str,
    account_name: str,
    confidence_score: float,
    match_reason: str,
    matched_keywords: list[str] | None = None,
    candidate_count: int = 0,
) -> dict[str, Any]:
    """
    Create the final mapped transaction dictionary.
    """

    return {
        "Date": transaction.get("Date"),
        "Payee": transaction.get("Payee", ""),
        "Account": transaction.get("Account", ""),
        "Memo": transaction.get("Memo", ""),
        "Store": transaction.get("Store", ""),
        "Payment": float(transaction.get("Payment", 0) or 0),
        "Deposit": float(transaction.get("Deposit", 0) or 0),
        "Amount": calculate_signed_amount(transaction),
        "Rule Name": rule_name,
        "Account Name": account_name,
        "Confidence Score": confidence_score,
        "Match Reason": match_reason,
        "Matched Keywords": ", ".join(matched_keywords or []),
        "Candidate Rule Count": candidate_count,
    }


def apply_rules(
    bank_df: pd.DataFrame,
    parsed_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Apply all parsed rules to all bank transactions.

    Parameters
    ----------
    bank_df : pd.DataFrame
        Cleaned bank statement dataframe.

    parsed_rules : list[dict[str, Any]]
        Rules produced by rule_parser.parse_rules().

    Returns
    -------
    list[dict[str, Any]]
        Mapped transaction records with confidence and audit details.
    """

    mapped_transactions = []

    for _, row in bank_df.iterrows():
        transaction = row.to_dict()

        best_rule, best_result, candidates = find_best_rule_match(
            transaction=transaction,
            parsed_rules=parsed_rules,
        )

        if best_rule and best_result:
            mapped_transactions.append(
                build_mapped_transaction(
                    transaction=transaction,
                    rule_name=best_rule.get("rule_name", ""),
                    account_name=best_rule.get("account_name", ""),
                    confidence_score=best_result.confidence_score,
                    match_reason=best_result.match_reason,
                    matched_keywords=best_result.matched_keywords,
                    candidate_count=len(candidates),
                )
            )
        else:
            mapped_transactions.append(
                build_mapped_transaction(
                    transaction=transaction,
                    rule_name="Unmatched",
                    account_name="Unmapped",
                    confidence_score=0.0,
                    match_reason="No eligible rule matched this transaction.",
                    matched_keywords=[],
                    candidate_count=0,
                )
            )

    return mapped_transactions
