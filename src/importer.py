"""
importer.py

Clean ETL ingestion layer for GL Mapping system.

Supports:
- .xlsx
- .csv

Responsibilities:
- Load data safely
- Validate schema
- Clean fields
- Combine multiple bank statements
- Extract Brand / Store ID metadata from file names when needed
"""

from pathlib import Path

import pandas as pd

from utils import validate_columns


# ---------------------------
# SAFE FILE READER
# ---------------------------
def read_data_file(file_path: str | Path, header: int = 0) -> pd.DataFrame:
    """
    Reads CSV or Excel file safely.

    Parameters
    ----------
    file_path : str | Path
        Path of the input file.

    header : int
        Row number to use as the column header.

    Returns
    -------
    pd.DataFrame
        Loaded dataframe.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.

    ValueError
        If the file type is unsupported.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_extension = file_path.suffix.lower()

    if file_extension == ".csv":
        return pd.read_csv(file_path)

    if file_extension == ".xlsx":
        return pd.read_excel(
            file_path,
            header=header,
            engine="openpyxl",
        )

    raise ValueError(f"Unsupported file format: {file_extension}")


def extract_store_id_from_filename(file_path: str | Path) -> str:
    """
    Extract store ID from filename.

    Examples
    --------
    bank_statement_dd13.xlsx -> DD13
    bank_statement_dd14.xlsx -> DD14

    Parameters
    ----------
    file_path : str | Path
        Bank statement file path.

    Returns
    -------
    str
        Store ID if found, otherwise empty string.
    """

    file_stem = Path(file_path).stem.upper()

    for part in file_stem.replace("-", "_").split("_"):
        if part.startswith("DD") and part[2:].isdigit():
            return part

    return ""


def build_store_name_from_file(file_path: str | Path, brand_name: str = "Dunkin") -> str:
    """
    Build standard Store value using file name.

    Example
    -------
    bank_statement_dd14.xlsx -> Dunkin:DD14

    Parameters
    ----------
    file_path : str | Path
        Bank statement file path.

    brand_name : str
        Brand name to use.

    Returns
    -------
    str
        Store string in Brand:StoreID format.
    """

    store_id = extract_store_id_from_filename(file_path)

    if not store_id:
        return ""

    return f"{brand_name}:{store_id}"


# ---------------------------
# BANK STATEMENT
# ---------------------------
def load_bank_statement(file_path: str | Path) -> pd.DataFrame:
    """
    Load and clean one bank statement.

    Parameters
    ----------
    file_path : str | Path
        Path to one bank statement Excel file.

    Returns
    -------
    pd.DataFrame
        Cleaned bank statement dataframe.
    """

    df = read_data_file(file_path, header=1)

    required_columns = [
        "Date",
        "Payee",
        "Account",
        "Memo",
        "Payment",
        "Deposit",
        "Store",
        "Balance",
    ]

    validate_columns(df, required_columns)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in ["Payment", "Deposit", "Balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ["Payee", "Account", "Memo", "Store"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df.dropna(subset=["Date"]).reset_index(drop=True)

    return df


def load_bank_statements(file_paths: list[str | Path]) -> pd.DataFrame:
    """
    Load and combine multiple bank statement files.

    This function also fixes the demo DD13/DD14 issue.

    If a file is named:
        bank_statement_dd13.xlsx
        bank_statement_dd14.xlsx

    then Store will be overwritten as:
        Dunkin:DD13
        Dunkin:DD14

    This ensures the dashboard can filter by Store ID correctly.

    Parameters
    ----------
    file_paths : list[str | Path]
        List of bank statement Excel file paths.

    Returns
    -------
    pd.DataFrame
        Combined bank statement dataframe.
    """

    all_bank_dfs = []

    for file_path in file_paths:
        file_path = Path(file_path)
        bank_df = load_bank_statement(file_path)

        source_file = file_path.name
        resolved_store = build_store_name_from_file(file_path)

        bank_df["Source File"] = source_file

        if resolved_store:
            bank_df["Store"] = resolved_store

        all_bank_dfs.append(bank_df)

    if not all_bank_dfs:
        raise ValueError("No bank statement files were loaded.")

    combined_df = pd.concat(all_bank_dfs, ignore_index=True)

    return combined_df


# ---------------------------
# RULES
# ---------------------------
def load_bank_feed_rules(file_path: str | Path) -> pd.DataFrame:
    """
    Load bank feed rules.

    Parameters
    ----------
    file_path : str | Path
        Path to bank_feed_rules.xlsx.

    Returns
    -------
    pd.DataFrame
        Rules dataframe.
    """

    df = read_data_file(file_path)

    required_columns = [
        "Rule Name",
        "Rule Conditions",
        "Rule Outputs",
    ]

    validate_columns(df, required_columns)

    return df.fillna("")


# ---------------------------
# COA
# ---------------------------
def load_chart_of_accounts(file_path: str | Path) -> pd.DataFrame:
    """
    Load chart of accounts.

    Parameters
    ----------
    file_path : str | Path
        Path to chart_of_accounts.csv.

    Returns
    -------
    pd.DataFrame
        Cleaned chart of accounts dataframe.
    """

    df = read_data_file(file_path)

    required_columns = [
        "Account number",
        "Account name",
        "Account type",
        "Detail type",
    ]

    validate_columns(df, required_columns)

    for col in required_columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df