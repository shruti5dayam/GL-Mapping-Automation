"""
coa_lookup.py

Looks up Chart of Accounts (COA) information for mapped transactions.

Responsibilities:
- Match Account Name to the Chart of Accounts
- Add Account Number
- Add Account Type
- Add Detail Type

Author: Shruti GL Mapping Project
"""

import pandas as pd


def build_coa_lookup(coa_df: pd.DataFrame) -> dict:
    """
    Build a lookup dictionary from the Chart of Accounts.

    Parameters
    ----------
    coa_df : pd.DataFrame
        Chart of Accounts dataframe.

    Returns
    -------
    dict
        Dictionary keyed by Account Name.
    """

    lookup = {}

    for _, row in coa_df.iterrows():

        account_name = row["Account name"].strip()

        lookup[account_name] = {
            "Account Number": row["Account number"],
            "Account Type": row["Account type"],
            "Detail Type": row["Detail type"],
        }

    return lookup

def enrich_transactions(mapped_transactions: list,
                        coa_lookup: dict) -> list:

    enriched_transactions = []

    for transaction in mapped_transactions:

        account_name = transaction["Account Name"]

        coa = coa_lookup.get(account_name)

        if coa:

            transaction["Account Number"] = coa["Account Number"]
            transaction["Account Type"] = coa["Account Type"]
            transaction["Detail Type"] = coa["Detail Type"]

            # 🔥 NEW FIX: add grouping for P&L
            transaction["Account Group"] = coa["Account Type"]

        else:

            transaction["Account Number"] = ""
            transaction["Account Type"] = "Unknown"
            transaction["Detail Type"] = "Unknown"
            transaction["Account Group"] = "Unknown"

        enriched_transactions.append(transaction)

    return enriched_transactions