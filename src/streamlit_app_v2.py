"""
Streamlit V2 UI for GL Mapping Automation.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from pipeline import run_pipeline


st.set_page_config(
    page_title="GL Mapping Automation V2",
    page_icon="📊",
    layout="wide",
)

st.title("📊 GL Mapping Automation V2")
st.caption("Upload files → Run GL Mapping → Review outputs")


RESULTS_KEY = "gl_mapping_v2_results"


def format_money(value: float) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def make_display_safe(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    display_df = df.copy()

    for col in display_df.columns:
        if pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime("%Y-%m-%d")

    return display_df


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df.empty:
        return b""

    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str) -> bytes:
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

    buffer.seek(0)
    return buffer.getvalue()


def get_net_income(pnl_df: pd.DataFrame) -> float:
    if pnl_df.empty or "Particulars" not in pnl_df.columns:
        return 0.0

    net_income_row = pnl_df[
        pnl_df["Particulars"].astype(str).str.lower() == "net income"
    ]

    if net_income_row.empty:
        return 0.0

    amount_column = "$" if "$" in pnl_df.columns else "Amount"

    value = pd.to_numeric(
        net_income_row.iloc[0][amount_column],
        errors="coerce",
    )

    if pd.isna(value):
        return 0.0

    return float(value)


def calculate_balance_summary(bank_df: pd.DataFrame) -> dict[str, float]:
    if bank_df.empty or "Balance" not in bank_df.columns:
        return {
            "opening_balance": 0.0,
            "closing_balance": 0.0,
            "movement": 0.0,
        }

    df = bank_df.copy()
    df = df.reset_index(drop=True)

    balances = pd.to_numeric(df["Balance"], errors="coerce").dropna()

    if balances.empty:
        return {
            "opening_balance": 0.0,
            "closing_balance": 0.0,
            "movement": 0.0,
        }

    opening_balance = float(balances.iloc[0])
    closing_balance = float(balances.iloc[-1])

    return {
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "movement": closing_balance - opening_balance,
    }


def score_header(df: pd.DataFrame, expected_columns: set[str]) -> int:
    actual_columns = {str(col).strip().lower() for col in df.columns}
    return len(actual_columns.intersection(expected_columns))


def read_excel_with_best_header(
    uploaded_file,
    expected_columns: set[str],
    header_candidates: tuple[int, ...] = (0, 1, 2),
) -> pd.DataFrame:
    best_df = None
    best_score = -1

    for header in header_candidates:
        try:
            uploaded_file.seek(0)
            candidate_df = pd.read_excel(
                uploaded_file,
                header=header,
                engine="openpyxl",
            )

            current_score = score_header(candidate_df, expected_columns)

            if current_score > best_score:
                best_score = current_score
                best_df = candidate_df.copy()

        except Exception:
            continue

    if best_df is None:
        raise ValueError(f"Could not read Excel file: {uploaded_file.name}")

    return best_df


def read_uploaded_bank_files(uploaded_files) -> pd.DataFrame:
    expected_bank_columns = {
        "date", "payee", "account", "memo",
        "payment", "deposit", "store", "balance",
    }

    bank_dfs = []

    for uploaded_file in uploaded_files:
        bank_df = read_excel_with_best_header(
            uploaded_file,
            expected_bank_columns,
        )

        bank_df["Source File"] = uploaded_file.name
        bank_dfs.append(bank_df)

    if not bank_dfs:
        return pd.DataFrame()

    return pd.concat(bank_dfs, ignore_index=True)


def read_rules_file(uploaded_file) -> pd.DataFrame:
    expected_rule_columns = {
        "rule name",
        "rule conditions",
        "rule outputs",
    }

    return read_excel_with_best_header(
        uploaded_file,
        expected_rule_columns,
        header_candidates=(0, 1),
    )


def read_coa_file(uploaded_file) -> pd.DataFrame:
    uploaded_file.seek(0)

    try:
        return pd.read_csv(uploaded_file)
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding="utf-8-sig")


def get_result_df(results: dict, key: str) -> pd.DataFrame:
    value = results.get(key, pd.DataFrame())
    return value if isinstance(value, pd.DataFrame) else pd.DataFrame()


st.sidebar.header("Upload Input Files")

uploaded_bank_files = st.sidebar.file_uploader(
    "Bank Statements (.xlsx)",
    type=["xlsx"],
    accept_multiple_files=True,
)

uploaded_rules_file = st.sidebar.file_uploader(
    "Bank Feed Rules (.xlsx)",
    type=["xlsx"],
)

uploaded_coa_file = st.sidebar.file_uploader(
    "Chart of Accounts (.csv)",
    type=["csv"],
)

run_button = st.sidebar.button("🚀 Run GL Mapping", width="stretch")
clear_button = st.sidebar.button("🧹 Clear Results", width="stretch")

if clear_button:
    st.session_state.pop(RESULTS_KEY, None)
    st.rerun()


if run_button:
    if not uploaded_bank_files:
        st.error("Please upload at least one bank statement.")
        st.stop()

    if uploaded_rules_file is None:
        st.error("Please upload the bank feed rules file.")
        st.stop()

    if uploaded_coa_file is None:
        st.error("Please upload the chart of accounts file.")
        st.stop()

    try:
        with st.spinner("Reading uploaded files..."):
            bank_df = read_uploaded_bank_files(uploaded_bank_files)
            rules_df = read_rules_file(uploaded_rules_file)
            coa_df = read_coa_file(uploaded_coa_file)

        with st.spinner("Running GL Mapping pipeline..."):
            results = run_pipeline(
                bank_df=bank_df,
                rules_df=rules_df,
                coa_df=coa_df,
            )

        st.session_state[RESULTS_KEY] = results
        st.success("Pipeline completed successfully.")

    except Exception as error:
        st.error(f"Pipeline failed: {error}")
        st.stop()


results = st.session_state.get(RESULTS_KEY)

if not results:
    st.info(
        "Upload bank statements, bank feed rules, and chart of accounts, "
        "then click **Run GL Mapping**."
    )
    st.stop()


bank_df = get_result_df(results, "bank_df")
mapping_audit_df = get_result_df(results, "mapping_audit_df")
trial_balance_df = get_result_df(results, "trial_balance_df")
pnl_df = get_result_df(results, "pnl_df")
unmatched_df = get_result_df(results, "unmatched_df")
low_confidence_df = get_result_df(results, "low_confidence_df")
rule_usage_df = get_result_df(results, "rule_usage_df")
account_usage_df = get_result_df(results, "account_usage_df")
validation_report = results.get("validation_report", {})


st.subheader("Bank Balance Summary")

balance_summary = calculate_balance_summary(bank_df)

bal_col1, bal_col2, bal_col3 = st.columns(3)

with bal_col1:
    st.metric(
        "Opening Balance",
        format_money(balance_summary["opening_balance"]),
    )

with bal_col2:
    st.metric(
        "Closing Balance",
        format_money(balance_summary["closing_balance"]),
    )

with bal_col3:
    st.metric(
        "Balance Movement",
        format_money(balance_summary["movement"]),
    )


st.subheader("Pipeline Summary")

total_transactions = validation_report.get("total_transactions", len(mapping_audit_df))
unmatched_count = validation_report.get("unmatched_rules", len(unmatched_df))
low_confidence_count = validation_report.get(
    "low_confidence_mappings",
    len(low_confidence_df),
)
total_signed_amount = validation_report.get("total_signed_amount", 0.0)

mapped_count = total_transactions - unmatched_count

mapping_percentage = (
    mapped_count / total_transactions * 100
    if total_transactions
    else 0.0
)

sum_col1, sum_col2, sum_col3, sum_col4, sum_col5 = st.columns(5)

with sum_col1:
    st.metric("Transactions", total_transactions)

with sum_col2:
    st.metric("Mapped", mapped_count)

with sum_col3:
    st.metric("Unmatched", unmatched_count)

with sum_col4:
    st.metric("Mapping %", f"{mapping_percentage:.2f}%")

with sum_col5:
    st.metric("Net Movement", format_money(total_signed_amount))


tab_pnl, tab_tb, tab_audit, tab_unmatched, tab_low, tab_rules, tab_accounts = st.tabs(
    [
        "P&L",
        "Trial Balance",
        "Mapping Audit",
        "Unmatched",
        "Low Confidence",
        "Rule Usage",
        "Account Usage",
    ]
)


with tab_pnl:
    st.subheader("Profit & Loss")

    if pnl_df.empty:
        st.warning("No P&L data available.")
    else:
        st.dataframe(
            make_display_safe(pnl_df).style.format({"$": "{:,.2f}"}),
            width="stretch",
            hide_index=True,
        )

        net_income = get_net_income(pnl_df)
        st.success(f"Net Income: {format_money(net_income)}")

        st.download_button(
            "Download P&L Excel",
            data=dataframe_to_excel_bytes(pnl_df, "P&L"),
            file_name="pnl.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


with tab_tb:
    st.subheader("Trial Balance")

    if trial_balance_df.empty:
        st.warning("No Trial Balance data available.")
    else:
        st.dataframe(
            make_display_safe(trial_balance_df).style.format({"Amount": "{:,.2f}"}),
            width="stretch",
            hide_index=True,
        )

        st.download_button(
            "Download Trial Balance Excel",
            data=dataframe_to_excel_bytes(trial_balance_df, "Trial Balance"),
            file_name="trial_balance.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


with tab_audit:
    st.subheader("Mapping Audit")

    if mapping_audit_df.empty:
        st.warning("No mapping audit data available.")
    else:
        st.dataframe(
            make_display_safe(mapping_audit_df),
            width="stretch",
            hide_index=True,
        )

        st.download_button(
            "Download Mapping Audit CSV",
            data=dataframe_to_csv_bytes(mapping_audit_df),
            file_name="mapping_audit.csv",
            mime="text/csv",
        )


with tab_unmatched:
    st.subheader("Unmatched Transactions")
    st.metric("Unmatched Count", len(unmatched_df))

    if unmatched_df.empty:
        st.success("No unmatched transactions.")
    else:
        st.dataframe(
            make_display_safe(unmatched_df),
            width="stretch",
            hide_index=True,
        )


with tab_low:
    st.subheader("Low Confidence Transactions")
    st.metric("Low Confidence Count", len(low_confidence_df))

    if low_confidence_df.empty:
        st.success("No low-confidence transactions.")
    else:
        st.dataframe(
            make_display_safe(low_confidence_df),
            width="stretch",
            hide_index=True,
        )


with tab_rules:
    st.subheader("Rule Usage")

    if rule_usage_df.empty:
        st.warning("No rule usage data available.")
    else:
        st.dataframe(
            make_display_safe(rule_usage_df).style.format(
                {
                    "Total_Amount": "{:,.2f}",
                    "Average_Confidence": "{:,.2f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )


with tab_accounts:
    st.subheader("Account Usage")

    if account_usage_df.empty:
        st.warning("No account usage data available.")
    else:
        st.dataframe(
            make_display_safe(account_usage_df).style.format(
                {
                    "Total_Amount": "{:,.2f}",
                    "Average_Confidence": "{:,.2f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )