"""
trial_balance.py

Generates the Trial Balance from enriched transactions.

Responsibilities:
- Group transactions by Account
- Calculate total balance
- Sort accounts
- Return Trial Balance DataFrame

Author: Shruti GL Mapping Project
"""

import pandas as pd


def generate_trial_balance(enriched_transactions: list) -> pd.DataFrame:
    """
    Generate the Trial Balance.

    Parameters
    ----------
    enriched_transactions : list
        Transactions enriched with COA information.

    Returns
    -------
    pd.DataFrame
        Trial Balance dataframe.
    """

    trial_balance_df = pd.DataFrame(
        enriched_transactions
    )

    if trial_balance_df.empty:
        return trial_balance_df

    trial_balance_df = (
        trial_balance_df
        .groupby(
            [
                "Account Number",
                "Account Name",
                "Account Type",
                "Detail Type",
            ],
            as_index=False,
        )["Amount"]
        .sum()
    )

    trial_balance_df = trial_balance_df.sort_values(
        by=[
            "Account Type",
            "Account Name",
        ]
    ).reset_index(drop=True)

    return trial_balance_df


def save_trial_balance(
    trial_balance_df: pd.DataFrame,
    output_file: str,
) -> None:
    """
    Save the Trial Balance to Excel.

    Parameters
    ----------
    trial_balance_df : pd.DataFrame
        Trial Balance dataframe.

    output_file : str
        Output Excel file path.

    Returns
    -------
    None
    """

    trial_balance_df.to_excel(
        output_file,
        index=False,
    )