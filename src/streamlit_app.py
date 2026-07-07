"""
Streamlit UI for GL Mapping Project.

Run from project root:
    streamlit run src/streamlit_app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from pnl_generator import generate_pnl


# =========================================================
# PATH CONFIG
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"

PNL_FILE = OUTPUT_DIR / "pnl.xlsx"
TRIAL_BALANCE_FILE = OUTPUT_DIR / "trial_balance.xlsx"
MAPPING_AUDIT_FILE = OUTPUT_DIR / "mapping_audit.xlsx"


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="GL Mapping Dashboard",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# LOADERS
# =========================================================
@st.cache_data
def _load_excel_cached(path: str, sheet_name=0, modified_time: int = 0) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)


def load_excel(file_path: Path, sheet_name=0) -> pd.DataFrame:
    if not file_path.exists():
        return pd.DataFrame()

    return _load_excel_cached(
        str(file_path),
        sheet_name,
        file_path.stat().st_mtime_ns,
    )


@st.cache_data
def _load_mapping_audit_cached(path: str, modified_time: int = 0) -> dict:
    return pd.read_excel(path, sheet_name=None)


def load_mapping_audit_sheets(file_path: Path) -> dict:
    if not file_path.exists():
        return {}

    return _load_mapping_audit_cached(
        str(file_path),
        file_path.stat().st_mtime_ns,
    )


# =========================================================
# HELPERS
# =========================================================
def format_money(value: float) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def add_filter_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds Brand, Store ID, and Period columns.

    Expected Store format:
        Dunkin:DD13
        Dunkin:DD14
    """

    df = df.copy()

    if df.empty:
        df["Brand"] = ""
        df["Store ID"] = ""
        df["Period"] = ""
        return df

    if "Store" in df.columns:
        store_text = df["Store"].fillna("").astype(str)
        store_parts = store_text.str.split(":", n=1, expand=True)

        df["Brand"] = store_parts[0].replace("", "Unknown")

        if store_parts.shape[1] > 1:
            df["Store ID"] = store_parts[1].str.upper().str.strip()
        else:
            df["Store ID"] = ""

    else:
        df["Brand"] = "Unknown"
        df["Store ID"] = ""

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Period"] = df["Date"].dt.to_period("M").astype(str)
        df["Period"] = df["Period"].replace("NaT", "")
    else:
        df["Period"] = ""

    return df


def apply_filters(
    df: pd.DataFrame,
    selected_brand: str,
    selected_store: str,
    selected_period: str,
) -> pd.DataFrame:
    """Apply sidebar filters to a dataframe."""

    if df.empty:
        return df

    filtered_df = df.copy()

    if selected_brand != "All" and "Brand" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Brand"] == selected_brand]

    if selected_store != "All" and "Store ID" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Store ID"] == selected_store]

    if selected_period != "All" and "Period" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Period"] == selected_period]

    return filtered_df


def build_trial_balance_from_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build filtered Trial Balance from mapping audit rows.

    Important:
    We do NOT flip signs here.

    Your backend Trial Balance uses:
        Deposits  = positive
        Payments  = negative

    Your pnl_generator.py already calculates:
        Gross Profit = income - abs(cogs)
        Net Income   = gross_profit - abs(expenses)

    So flipping Income here would make the dashboard wrong.
    """

    if df.empty:
        return pd.DataFrame()

    required_columns = [
        "Account Number",
        "Account Name",
        "Account Type",
        "Detail Type",
        "Amount",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"Missing columns for filtered Trial Balance: {missing_columns}")
        return pd.DataFrame()

    tb_df = df.copy()
    tb_df["Amount"] = pd.to_numeric(tb_df["Amount"], errors="coerce").fillna(0.0)

    return (
        tb_df.groupby(
            [
                "Account Number",
                "Account Name",
                "Account Type",
                "Detail Type",
            ],
            as_index=False,
        )["Amount"]
        .sum()
        .sort_values(["Account Type", "Account Name"])
        .reset_index(drop=True)
    )

def make_display_safe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare dataframe for Streamlit display while preserving numeric columns.
    """

    df = df.copy()

    # Convert numeric columns safely
    if "$" in df.columns:
        df["$"] = pd.to_numeric(df["$"], errors="coerce").astype("Float64")

    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").astype("Float64")

    # Blank spacer rows should appear empty instead of "None"
    if "Particulars" in df.columns:
        df["Particulars"] = df["Particulars"].fillna("")

    return df


def get_net_income(pnl_df: pd.DataFrame) -> float:
    """Extract Net Income from P&L dataframe."""

    if pnl_df.empty or "Particulars" not in pnl_df.columns:
        return 0.0

    amount_column = "$" if "$" in pnl_df.columns else "Amount"

    if amount_column not in pnl_df.columns:
        return 0.0

    net_income_row = pnl_df[
        pnl_df["Particulars"].astype(str).str.lower() == "net income"
    ]

    if net_income_row.empty:
        return 0.0

    value = pd.to_numeric(net_income_row.iloc[0][amount_column], errors="coerce")

    if pd.isna(value):
        return 0.0

    return float(value)


# =========================================================
# HEADER
# =========================================================
st.title("📊 GL Mapping Automation Dashboard")
st.caption("Bank Statement → Rule Engine → COA Mapping → Trial Balance → P&L")


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Output Files")
st.sidebar.write(f"P&L: `{PNL_FILE.relative_to(PROJECT_ROOT)}`")
st.sidebar.write(f"Trial Balance: `{TRIAL_BALANCE_FILE.relative_to(PROJECT_ROOT)}`")
st.sidebar.write(f"Mapping Audit: `{MAPPING_AUDIT_FILE.relative_to(PROJECT_ROOT)}`")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()


# =========================================================
# FILE CHECK
# =========================================================
if not TRIAL_BALANCE_FILE.exists() or not MAPPING_AUDIT_FILE.exists():
    st.error(
        "Output files not found. First run `python3 src/main.py`, "
        "then run this dashboard again."
    )
    st.stop()


# =========================================================
# LOAD DATA
# =========================================================
trial_balance_df = load_excel(TRIAL_BALANCE_FILE)
pnl_df = load_excel(PNL_FILE)
audit_sheets = load_mapping_audit_sheets(MAPPING_AUDIT_FILE)

mapping_audit_df = audit_sheets.get("Mapping Audit", pd.DataFrame())
unmatched_df = audit_sheets.get("Unmatched", pd.DataFrame())
low_confidence_df = audit_sheets.get("Low Confidence", pd.DataFrame())
rule_usage_df = audit_sheets.get("Rule Usage", pd.DataFrame())
account_usage_df = audit_sheets.get("Account Usage", pd.DataFrame())

mapping_audit_df = add_filter_columns(mapping_audit_df)
unmatched_df = add_filter_columns(unmatched_df)
low_confidence_df = add_filter_columns(low_confidence_df)


# =========================================================
# FILTERS
# =========================================================
st.sidebar.header("Filters")

brand_options = ["All"] + sorted(
    mapping_audit_df["Brand"].dropna().astype(str).unique().tolist()
)

store_options = ["All"] + sorted(
    mapping_audit_df["Store ID"].dropna().astype(str).unique().tolist()
)

period_options = ["All"] + sorted(
    mapping_audit_df["Period"].dropna().astype(str).unique().tolist()
)

selected_brand = st.sidebar.selectbox("Brand", brand_options)
selected_store = st.sidebar.selectbox("Store ID", store_options)
selected_period = st.sidebar.selectbox("Period", period_options)

filtered_df = apply_filters(
    mapping_audit_df,
    selected_brand,
    selected_store,
    selected_period,
)

filtered_unmatched_df = apply_filters(
    unmatched_df,
    selected_brand,
    selected_store,
    selected_period,
)

filtered_low_confidence_df = apply_filters(
    low_confidence_df,
    selected_brand,
    selected_store,
    selected_period,
)


# =========================================================
# FILTERED P&L + TRIAL BALANCE
# =========================================================
is_all_filter = (
    selected_brand == "All"
    and selected_store == "All"
    and selected_period == "All"
)

filtered_trial_balance_df = build_trial_balance_from_transactions(filtered_df)

# Debug
print(filtered_trial_balance_df[["Account Name", "Amount"]])

if is_all_filter:
    filtered_pnl_df = pnl_df.copy()

else:
    if filtered_trial_balance_df.empty:
        filtered_pnl_df = pd.DataFrame()
    else:
        filtered_pnl_df = generate_pnl(filtered_trial_balance_df)

filtered_pnl_df = make_display_safe(filtered_pnl_df)


# =========================================================
# KPI CARDS
# =========================================================
st.subheader("Pipeline Summary")

total_transactions = len(filtered_df)
unmatched_count = len(filtered_unmatched_df)
low_confidence_count = len(filtered_low_confidence_df)

if "Amount" in filtered_df.columns:
    total_signed_amount = pd.to_numeric(
        filtered_df["Amount"],
        errors="coerce",
    ).fillna(0.0).sum()
else:
    total_signed_amount = 0.0

mapped_count = total_transactions - unmatched_count
mapping_percentage = (
    mapped_count / total_transactions * 100
    if total_transactions
    else 0
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Transactions", total_transactions)

with col2:
    st.metric("Mapped", mapped_count)

with col3:
    st.metric("Unmatched", unmatched_count)

with col4:
    st.metric("Mapping %", f"{mapping_percentage:.2f}%")

with col5:
    st.metric("Net Bank Movement", format_money(total_signed_amount))


st.info(
    f"Showing data for Brand: **{selected_brand}**, "
    f"Store ID: **{selected_store}**, "
    f"Period: **{selected_period}**"
)


# =========================================================
# P&L VIEW
# =========================================================

st.subheader("Profit & Loss")

if filtered_pnl_df.empty:
    st.warning("No P&L data available for selected filters.")
else:
    st.dataframe(
        make_display_safe(filtered_pnl_df).style.format({
            "$": "{:,.2f}"
        }),
        width="stretch",
        hide_index=True,
)

    net_income = get_net_income(filtered_pnl_df)
    st.success(f"Net Income: {format_money(net_income)}")



# =========================================================
# TRIAL BALANCE VIEW
# =========================================================
st.subheader("Trial Balance")

if filtered_trial_balance_df.empty:
    st.warning("No Trial Balance data available for selected filters.")
else: 

    st.dataframe(
    make_display_safe(filtered_trial_balance_df).style.format({
        "Amount": "{:,.2f}"
    }),
    width="stretch",
    hide_index=True,
    )


# =========================================================
# AUDIT TABS
# =========================================================
st.subheader("Mapping Audit Review")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Mapping Audit",
        "Unmatched",
        "Low Confidence",
        "Rule Usage",
        "Account Usage",
    ]
)

with tab1:
    st.write("Every transaction with selected rule, confidence score, and match reason.")
    st.dataframe(make_display_safe(filtered_df), width="stretch", hide_index=True)

with tab2:
    st.write("Transactions that did not find a matching rule.")
    st.dataframe(
        make_display_safe(filtered_unmatched_df),
        width="stretch",
        hide_index=True,
    )

with tab3:
    st.write("Mapped transactions that need manual review because confidence is low.")
    st.dataframe(
        make_display_safe(filtered_low_confidence_df),
        width="stretch",
        hide_index=True,
    )

with tab4:
    st.write("Rule usage summary.")
    st.dataframe(make_display_safe(rule_usage_df), width="stretch", hide_index=True)

with tab5:
    st.write("Account usage summary.")
    st.dataframe(make_display_safe(account_usage_df), width="stretch", hide_index=True)


# =========================================================
# DOWNLOAD BUTTONS
# =========================================================
st.subheader("Download Outputs")

col_a, col_b, col_c = st.columns(3)

with col_a:
    if PNL_FILE.exists():
        with open(PNL_FILE, "rb") as file:
            st.download_button(
                "Download Full P&L",
                data=file,
                file_name="pnl.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with col_b:
    if TRIAL_BALANCE_FILE.exists():
        with open(TRIAL_BALANCE_FILE, "rb") as file:
            st.download_button(
                "Download Full Trial Balance",
                data=file,
                file_name="trial_balance.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with col_c:
    if MAPPING_AUDIT_FILE.exists():
        with open(MAPPING_AUDIT_FILE, "rb") as file:
            st.download_button(
                "Download Mapping Audit",
                data=file,
                file_name="mapping_audit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )