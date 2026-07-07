"""
validators.py

Improved validation layer for GL Mapping Automation.

Adds richer audit checks:
- unmatched transactions
- true COA lookup failures
- blank account numbers inside valid COA rows
- invalid amounts
- both Payment and Deposit filled
- zero amount rows
- low-confidence mappings
- multiple candidate rule matches
- rule usage summary
- account usage summary
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


LOW_CONFIDENCE_THRESHOLD = 60.0


def _to_dataframe(mapped_transactions: list[dict[str, Any]]) -> pd.DataFrame:
    """
    Convert mapped transaction list into a dataframe safely.
    """

    return pd.DataFrame(mapped_transactions)


def validate_mapped_transactions(
    mapped_transactions: list[dict[str, Any]],
    low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    """
    Run validation checks on mapped transactions.

    Parameters
    ----------
    mapped_transactions : list[dict[str, Any]]
        Output after rule engine and COA enrichment.

    low_confidence_threshold : float
        Any mapped transaction below this score should be reviewed manually.

    Returns
    -------
    dict[str, Any]
        Validation report with counts and summary tables.
    """

    df = _to_dataframe(mapped_transactions)

    if df.empty:
        return {
            "total_transactions": 0,
            "unmatched_rules": 0,
            "true_missing_coa_mapping": 0,
            "blank_account_number_in_coa": 0,
            "invalid_amounts": 0,
            "both_payment_and_deposit": 0,
            "zero_amount_rows": 0,
            "low_confidence_mappings": 0,
            "multiple_candidate_rules": 0,
            "total_signed_amount": 0.0,
            "rule_usage": pd.DataFrame(),
            "account_usage": pd.DataFrame(),
        }

    report = {}
    report["total_transactions"] = len(df)

    report["unmatched_rules"] = int((df.get("Rule Name") == "Unmatched").sum())

    # True COA failure means enrichment did not find a valid account type.
    if "Account Type" in df.columns:
        report["true_missing_coa_mapping"] = int(
            (df["Account Type"] == "Unknown").sum()
        )
    else:
        report["true_missing_coa_mapping"] = 0

    # Blank account number is different from missing COA.
    # A COA row can exist but have a blank account number.
    if {"Account Number", "Account Type"}.issubset(df.columns):
        report["blank_account_number_in_coa"] = int(
            ((df["Account Number"] == "") & (df["Account Type"] != "Unknown")).sum()
        )
    else:
        report["blank_account_number_in_coa"] = 0

    if "Amount" in df.columns:
        report["invalid_amounts"] = int(df["Amount"].isna().sum())
        report["zero_amount_rows"] = int((df["Amount"] == 0).sum())
        report["total_signed_amount"] = round(float(df["Amount"].sum()), 2)
    else:
        report["invalid_amounts"] = 0
        report["zero_amount_rows"] = 0
        report["total_signed_amount"] = 0.0

    if {"Payment", "Deposit"}.issubset(df.columns):
        report["both_payment_and_deposit"] = int(
            ((df["Payment"] > 0) & (df["Deposit"] > 0)).sum()
        )
    else:
        report["both_payment_and_deposit"] = 0

    if "Confidence Score" in df.columns:
        report["low_confidence_mappings"] = int(
            (
                (df["Rule Name"] != "Unmatched")
                & (df["Confidence Score"] < low_confidence_threshold)
            ).sum()
        )
    else:
        report["low_confidence_mappings"] = 0

    if "Candidate Rule Count" in df.columns:
        report["multiple_candidate_rules"] = int(
            (df["Candidate Rule Count"] > 1).sum()
        )
    else:
        report["multiple_candidate_rules"] = 0

    report["rule_usage"] = build_rule_usage_report(df)
    report["account_usage"] = build_account_usage_report(df)

    return report


def build_rule_usage_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build summary of how often each rule was used.
    """

    if df.empty or "Rule Name" not in df.columns:
        return pd.DataFrame()

    return (
        df.groupby("Rule Name", dropna=False)
        .agg(
            Transaction_Count=("Rule Name", "size"),
            Total_Amount=("Amount", "sum"),
            Average_Confidence=("Confidence Score", "mean"),
        )
        .reset_index()
        .sort_values("Transaction_Count", ascending=False)
    )


def build_account_usage_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build summary of amount by mapped account.
    """

    if df.empty or "Account Name" not in df.columns:
        return pd.DataFrame()

    return (
        df.groupby(
            ["Account Name", "Account Type", "Detail Type"],
            dropna=False,
        )
        .agg(
            Transaction_Count=("Account Name", "size"),
            Total_Amount=("Amount", "sum"),
            Average_Confidence=("Confidence Score", "mean"),
        )
        .reset_index()
        .sort_values("Total_Amount", ascending=False)
    )


def build_mapping_audit_dataframe(
    mapped_transactions: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Create row-level audit dataframe for Excel export.

    This shows every bank row, the chosen rule, confidence score,
    and the reason why the rule was selected.
    """

    df = _to_dataframe(mapped_transactions)

    preferred_columns = [
        "Date",
        "Payee",
        "Account",
        "Memo",
        "Store",
        "Payment",
        "Deposit",
        "Amount",
        "Rule Name",
        "Account Name",
        "Account Number",
        "Account Type",
        "Detail Type",
        "Confidence Score",
        "Matched Keywords",
        "Candidate Rule Count",
        "Match Reason",
    ]

    existing_columns = [col for col in preferred_columns if col in df.columns]
    remaining_columns = [col for col in df.columns if col not in existing_columns]

    return df[existing_columns + remaining_columns]


def save_mapping_audit_report(
    mapped_transactions: list[dict[str, Any]],
    output_file: str | Path,
) -> None:
    """
    Save mapping audit report to Excel.

    Sheets
    ------
    Mapping Audit
        Every mapped transaction with confidence and reason.

    Rule Usage
        Count and amount by rule.

    Account Usage
        Count and amount by account.

    Low Confidence
        Rows needing human review.

    Unmatched
        Rows where no rule matched.
    """

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    audit_df = build_mapping_audit_dataframe(mapped_transactions)
    rule_usage_df = build_rule_usage_report(audit_df)
    account_usage_df = build_account_usage_report(audit_df)

    if "Confidence Score" in audit_df.columns:
        low_confidence_df = audit_df[
            (audit_df["Rule Name"] != "Unmatched")
            & (audit_df["Confidence Score"] < LOW_CONFIDENCE_THRESHOLD)
        ]
    else:
        low_confidence_df = pd.DataFrame()

    if "Rule Name" in audit_df.columns:
        unmatched_df = audit_df[audit_df["Rule Name"] == "Unmatched"]
    else:
        unmatched_df = pd.DataFrame()

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        audit_df.to_excel(writer, sheet_name="Mapping Audit", index=False)
        rule_usage_df.to_excel(writer, sheet_name="Rule Usage", index=False)
        account_usage_df.to_excel(writer, sheet_name="Account Usage", index=False)
        low_confidence_df.to_excel(writer, sheet_name="Low Confidence", index=False)
        unmatched_df.to_excel(writer, sheet_name="Unmatched", index=False)


def print_validation_report(report: dict[str, Any]) -> None:
    """
    Pretty print validation results.
    """

    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    print(f"Total Transactions           : {report['total_transactions']}")
    print(f"Unmatched Rules              : {report['unmatched_rules']}")
    print(f"True Missing COA Mapping     : {report['true_missing_coa_mapping']}")
    print(f"Blank Account Number in COA  : {report['blank_account_number_in_coa']}")
    print(f"Invalid Amounts              : {report['invalid_amounts']}")
    print(f"Zero Amount Rows             : {report['zero_amount_rows']}")
    print(f"Both Payment and Deposit     : {report['both_payment_and_deposit']}")
    print(f"Low Confidence Mappings      : {report['low_confidence_mappings']}")
    print(f"Multiple Candidate Rules     : {report['multiple_candidate_rules']}")
    print(f"Total Signed Amount          : {report['total_signed_amount']:,.2f}")

    print("=" * 60)
