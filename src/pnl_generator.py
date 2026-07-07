"""
Custom Profit & Loss generator.

Creates P&L in manager-required format:
Income
Cost of Goods Sold
Gross Profit
Expenses
Net Operating Income
Net Income
"""

from pathlib import Path

import pandas as pd


PNL_ORDER = [
    ("section", "Income"),

    ("account", "Returns & Allowance"),
    ("blank", ""),

    ("account", "Sales"),
    ("account", "Promotion Refunds"),
    ("account", "Sales:Sales DD Mobile XXXXXX0378"),
    ("subtotal", "Total Sales"),
    ("blank", ""),

    ("subtotal", "Total Income"),
    ("blank", ""),

    ("section", "Cost of Goods Sold"),
    ("blank", ""),

    ("account", "Food Purchases"),
    ("account", "Food Purchases:LODI BR Purchases"),
    ("subtotal", "Total Food Purchases"),
    ("account", "Tillster Online Platform Fee"),
    ("blank", ""),

    ("subtotal", "Total Cost of Goods Sold"),
    ("blank", ""),

    ("calculated", "Gross Profit"),
    ("blank", ""),

    ("section", "Expenses"),

    ("account", "Adfund"),
    ("blank", ""),

    ("account", "Credit Card Charges"),
    ("account", "Credit Card Charges:Equifax Credit Card Loss Prevention Charges"),
    ("subtotal", "Total Credit Card Charges"),
    ("blank", ""),

    ("account", "Kiosk License Fee"),
    ("blank", ""),

    ("account", "Payroll Expenses"),
    ("account", "Payroll Expenses:Salary & Wages Others"),
    ("subtotal", "Total Payroll Expenses"),
    ("blank", ""),

    ("account", "Rent Expense"),
    ("blank", ""),

    ("account", "Royalties & Fees"),
    ("account", "Royalties & Fees:DD ORIG ID XXXXXX0378"),
    ("account", "Royalties & Fees:Royalty DBMASTERFINANC XXXXXX0378"),
    ("subtotal", "Total Royalties & Fees"),
    ("blank", ""),

    ("account", "Technology Expenses"),
    ("account", "Technology Expenses:Paytronix"),
    ("subtotal", "Total Technology Expenses"),
    ("blank", ""),

    ("account", "Utilities"),
    ("blank", ""),

    ("subtotal", "Total Expenses"),
    ("blank", ""),

    ("calculated", "Net Operating Income"),
    ("calculated", "Net Income"),
]


SUBTOTAL_GROUPS = {
    "Total Sales": [
        "Sales",
        "Promotion Refunds",
        "Sales:Sales DD Mobile XXXXXX0378",
    ],
    "Total Income": [
        "Returns & Allowance",
        "Sales",
        "Promotion Refunds",
        "Sales:Sales DD Mobile XXXXXX0378",
    ],
    "Total Food Purchases": [
        "Food Purchases",
        "Food Purchases:LODI BR Purchases",
    ],
    "Total Cost of Goods Sold": [
        "Food Purchases",
        "Food Purchases:LODI BR Purchases",
        "Tillster Online Platform Fee",
    ],
    "Total Credit Card Charges": [
        "Credit Card Charges",
        "Credit Card Charges:Equifax Credit Card Loss Prevention Charges",
    ],
    "Total Payroll Expenses": [
        "Payroll Expenses",
        "Payroll Expenses:Salary & Wages Others",
    ],
    "Total Royalties & Fees": [
        "Royalties & Fees",
        "Royalties & Fees:DD ORIG ID XXXXXX0378",
        "Royalties & Fees:Royalty DBMASTERFINANC XXXXXX0378",
    ],
    "Total Technology Expenses": [
        "Technology Expenses",
        "Technology Expenses:Paytronix",
    ],
    "Total Expenses": [
    "Adfund",
    "Credit Card Charges",
    "Credit Card Charges:Equifax Credit Card Loss Prevention Charges",
    "Insurance Expense",
    "Kiosk License Fee",
    "NYC Income Tax",
    "Payroll Expenses",
    "Payroll Expenses:SUTA",
    "Payroll Expenses:Salary & Wages Others",
    "Rent Expense",
    "Repairs and Maintenance",
    "Royalties & Fees",
    "Royalties & Fees:DD ORIG ID XXXXXX0378",
    "Royalties & Fees:Royalty DBMASTERFINANC XXXXXX0378",
    "Sanitation & Garbage Removal",
    "Technology Expenses",
    "Technology Expenses:Paytronix",
    "Utilities",
    ],
}


def build_amount_lookup(trial_balance_df: pd.DataFrame) -> dict[str, float]:
    """
    Create a lookup dictionary.

    Parameters
    ----------
    trial_balance_df : pd.DataFrame
        Trial Balance with Account Name and Amount columns.

    Returns
    -------
    dict[str, float]
        Dictionary in this format:
        Account Name -> Amount
    """

    amount_lookup = {}

    if trial_balance_df.empty:
        return amount_lookup

    for _, row in trial_balance_df.iterrows():
        account_name = str(row["Account Name"]).strip()
        amount = pd.to_numeric(row["Amount"], errors="coerce")

        if pd.isna(amount):
            amount = 0.0

        amount_lookup[account_name] = float(amount)

    return amount_lookup


def get_total(amount_lookup: dict[str, float], account_names: list[str]) -> float:
    """
    Add amounts for selected accounts.

    Parameters
    ----------
    amount_lookup : dict[str, float]
        Account Name -> Amount lookup.

    account_names : list[str]
        Accounts to add.

    Returns
    -------
    float
        Total amount. Missing accounts are treated as zero.
    """

    return float(sum(amount_lookup.get(account_name, 0.0) for account_name in account_names))


def generate_pnl(trial_balance_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate formatted P&L DataFrame.

    Parameters
    ----------
    trial_balance_df : pd.DataFrame
        Trial Balance dataframe.

    Returns
    -------
    pd.DataFrame
        P&L dataframe with:
        - Particulars
        - $

    Important
    ---------
    The $ column is kept numeric.
    Blank spacer rows use pd.NA instead of empty string.
    This prevents Streamlit/PyArrow dtype errors.
    """

    amount_lookup = build_amount_lookup(trial_balance_df)

    total_income = get_total(amount_lookup, SUBTOTAL_GROUPS["Total Income"])
    total_cogs = get_total(amount_lookup, SUBTOTAL_GROUPS["Total Cost of Goods Sold"])
    total_expenses = get_total(amount_lookup, SUBTOTAL_GROUPS["Total Expenses"])

    gross_profit = total_income - abs(total_cogs)
    net_income = gross_profit - abs(total_expenses)

    rows = []

    for row_type, label in PNL_ORDER:
        amount = pd.NA

        if row_type == "account":
            amount = amount_lookup.get(label, 0.0)

        elif row_type == "subtotal":
            amount = get_total(amount_lookup, SUBTOTAL_GROUPS[label])

        elif row_type == "calculated":
            if label == "Gross Profit":
                amount = gross_profit
            elif label in ("Net Operating Income", "Net Income"):
                amount = net_income


        rows.append(
           {
                "Particulars": label,
                "$": amount,
            }
       )

    pnl_df = pd.DataFrame(rows)

    pnl_df["$"] = pd.to_numeric(
        pnl_df["$"],
        errors="coerce",
    ).astype("Float64")

    return pnl_df


def print_pnl(pnl_df: pd.DataFrame) -> None:
    """
    Print P&L in terminal.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        Generated P&L dataframe.

    Returns
    -------
    None
    """

    print("\n" + "=" * 60)
    print("PROFIT AND LOSS STATEMENT")
    print("=" * 60)

    for _, row in pnl_df.iterrows():
        label = row["Particulars"]
        amount = row["$"]

        if pd.isna(amount):
            print("")
        else:
            print(f"{label:<45} {float(amount):>12,.2f}")

    print("=" * 60)


def save_pnl(pnl_df: pd.DataFrame, output_file: str | Path) -> None:
    """
    Save formatted P&L to Excel.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        Generated P&L dataframe.

    output_file : str | Path
        Output file path.

    Returns
    -------
    None
    """

    pnl_df.to_excel(output_file, index=False)