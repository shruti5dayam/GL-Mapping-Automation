"""
Reusable in-memory pipeline for GL Mapping Automation V2.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from rule_parser import parse_rules
from rule_engine import apply_rules
from coa_lookup import build_coa_lookup, enrich_transactions
from trial_balance import generate_trial_balance
from pnl_generator import generate_pnl
from validators import (
    LOW_CONFIDENCE_THRESHOLD,
    validate_mapped_transactions,
    build_mapping_audit_dataframe,
    build_rule_usage_report,
    build_account_usage_report,
)


def clean_bank_dataframe(bank_df: pd.DataFrame) -> pd.DataFrame:
    df = bank_df.copy()

    required_columns = [
        "Date", "Payee", "Account", "Memo",
        "Payment", "Deposit", "Store", "Balance",
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing bank statement columns: {missing}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in ["Payment", "Deposit", "Balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ["Payee", "Account", "Memo", "Store"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df.dropna(subset=["Date"]).reset_index(drop=True)

    return df


def clean_rules_dataframe(rules_df: pd.DataFrame) -> pd.DataFrame:
    df = rules_df.copy()

    required_columns = ["Rule Name", "Rule Conditions", "Rule Outputs"]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing rule columns: {missing}")

    return df.fillna("")


def clean_coa_dataframe(coa_df: pd.DataFrame) -> pd.DataFrame:
    df = coa_df.copy()

    required_columns = [
        "Account number",
        "Account name",
        "Account type",
        "Detail type",
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing COA columns: {missing}")

    for col in required_columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def run_pipeline(
    bank_df: pd.DataFrame,
    rules_df: pd.DataFrame,
    coa_df: pd.DataFrame,
) -> dict[str, Any]:
    cleaned_bank_df = clean_bank_dataframe(bank_df)
    cleaned_rules_df = clean_rules_dataframe(rules_df)
    cleaned_coa_df = clean_coa_dataframe(coa_df)

    parsed_rules = parse_rules(cleaned_rules_df)

    mapped_transactions = apply_rules(
        cleaned_bank_df,
        parsed_rules,
    )

    coa_lookup = build_coa_lookup(cleaned_coa_df)

    enriched_transactions = enrich_transactions(
        mapped_transactions,
        coa_lookup,
    )

    validation_report = validate_mapped_transactions(enriched_transactions)

    mapping_audit_df = build_mapping_audit_dataframe(enriched_transactions)
    trial_balance_df = generate_trial_balance(enriched_transactions)
    pnl_df = generate_pnl(trial_balance_df)

    rule_usage_df = build_rule_usage_report(mapping_audit_df)
    account_usage_df = build_account_usage_report(mapping_audit_df)

    unmatched_df = mapping_audit_df[
        mapping_audit_df["Rule Name"] == "Unmatched"
    ].copy()

    low_confidence_df = mapping_audit_df[
        (mapping_audit_df["Rule Name"] != "Unmatched")
        & (mapping_audit_df["Confidence Score"] < LOW_CONFIDENCE_THRESHOLD)
    ].copy()

    return {
        "bank_df": cleaned_bank_df,
        "mapping_audit_df": mapping_audit_df,
        "trial_balance_df": trial_balance_df,
        "pnl_df": pnl_df,
        "unmatched_df": unmatched_df,
        "low_confidence_df": low_confidence_df,
        "rule_usage_df": rule_usage_df,
        "account_usage_df": account_usage_df,
        "validation_report": validation_report,
    }