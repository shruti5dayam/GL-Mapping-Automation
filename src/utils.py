# utils.py

"""
Utility functions for GL Mapping project.

Responsibilities:
- Column validation
- Common reusable helpers
"""

import pandas as pd


def validate_columns(df: pd.DataFrame, required_columns: list) -> None:
    """
    Validate whether required columns exist in dataframe.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe to validate.

    required_columns : list
        List of required column names.

    Raises
    ------
    ValueError
        If any required column is missing.
    """

    missing_columns = []

    for col in required_columns:
        if col not in df.columns:
            missing_columns.append(col)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )


def safe_divide(a: float, b: float) -> float:
    """
    Safe division to avoid division by zero.

    Parameters
    ----------
    a : float
        Numerator

    b : float
        Denominator

    Returns
    -------
    float
        Result or 0 if division fails
    """

    if b == 0:
        return 0
    return a / b