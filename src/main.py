"""
Main entry point for GL Mapping System.

Pipeline:
Bank Statement → Rules → Rule Engine → COA → Validation → Trial Balance → P&L
"""

from pathlib import Path

from importer import (
    load_bank_statements,
    load_bank_feed_rules,
    load_chart_of_accounts,
)

from rule_parser import parse_rules
from rule_engine import apply_rules

from coa_lookup import (
    build_coa_lookup,
    enrich_transactions,
)

from trial_balance import (
    generate_trial_balance,
    save_trial_balance,
)

from pnl_generator import (
    generate_pnl,
    print_pnl,
    save_pnl,
)


from validators import (
    validate_mapped_transactions,
    print_validation_report,
    save_mapping_audit_report,
)


# =========================================================
# CONFIGURATION LAYER
# =========================================================
class Config:
    """
    Central configuration for all file paths.
    Keeps system flexible and maintainable.
    """

    BASE_DIR = Path("data")
    OUTPUT_DIR = Path("output")

    BANK_STATEMENTS = [
    BASE_DIR / "bank_statement_dd13.xlsx",
    BASE_DIR / "bank_statement_dd14.xlsx",]
    RULES = BASE_DIR / "bank_feed_rules.xlsx"
    COA = BASE_DIR / "chart_of_accounts.csv"

    TRIAL_BALANCE_OUTPUT = OUTPUT_DIR / "trial_balance.xlsx"
    PNL_OUTPUT = OUTPUT_DIR / "pnl.xlsx"

    MAPPING_AUDIT_OUTPUT = OUTPUT_DIR / "mapping_audit.xlsx"


# =========================================================
# PIPELINE STAGES
# =========================================================
def load_data():
    """Load all input datasets."""
    print("📥 Loading input files...")

    bank_dfs = load_bank_statements(Config.BANK_STATEMENTS)
    rules_df = load_bank_feed_rules(Config.RULES)
    coa_df = load_chart_of_accounts(Config.COA)

    print("✔ Data loaded successfully\n")

    return bank_dfs, rules_df, coa_df


def parse_rule_stage(rules_df):
    """Parse rules into executable format."""
    print("🧠 Parsing rules...")

    parsed_rules = parse_rules(rules_df)

    print("\n===== FIRST 5 PARSED RULES =====")
    for rule in parsed_rules[:5]:
        print(rule)

    print(f"✔ Parsed {len(parsed_rules)} rules\n")

    return parsed_rules


def rule_engine_stage(bank_df, parsed_rules):
    """Apply rules to transactions."""
    # 3. RULE ENGINE
    print("⚙️ Applying rules...")

    mapped_transactions = apply_rules(bank_df, parsed_rules)

    print(f"✔ Mapped {len(mapped_transactions)} transactions\n")

    # ---------- DEBUG ----------
    print("\n===== FIRST MAPPED TRANSACTION =====")
    print(mapped_transactions[0])
    # ---------------------------

    return mapped_transactions


def coa_enrichment_stage(mapped_transactions, coa_df):
    """Attach COA metadata."""
    print("🏦 Enriching with COA...")

    coa_lookup = build_coa_lookup(coa_df)

    print("\n===== FIRST 10 COA KEYS =====")
    for key in list(coa_lookup.keys())[:10]:
        print(key)

    enriched_transactions = enrich_transactions(
        mapped_transactions,
        coa_lookup,
    )

    print("✔ COA enrichment done\n")

    return enriched_transactions


def validation_stage(enriched_transactions):
    """Run validation checks and save mapping audit report."""
    print("🔍 Running validation checks...")

    report = validate_mapped_transactions(enriched_transactions)
    print_validation_report(report)

    save_mapping_audit_report(
        enriched_transactions,
        Config.MAPPING_AUDIT_OUTPUT,
    )

    print(f"✔ Mapping audit saved: {Config.MAPPING_AUDIT_OUTPUT}")
    print("✔ Validation completed\n")



def trial_balance_stage(enriched_transactions):
    """Generate trial balance and save it."""
    print("📊 Generating Trial Balance...")

    tb_df = generate_trial_balance(enriched_transactions)

    save_trial_balance(tb_df, Config.TRIAL_BALANCE_OUTPUT)

    print("✔ Trial Balance created\n")

    return tb_df


def pnl_stage(trial_balance_df):
    """Generate Profit & Loss statement."""
    print("📈 Generating P&L...")

    pnl_df = generate_pnl(trial_balance_df)

    print_pnl(pnl_df)

    save_pnl(pnl_df, Config.PNL_OUTPUT)

    print("\n🎉 Pipeline Completed Successfully!\n")


# =========================================================
# PIPELINE ORCHESTRATOR
# =========================================================
def run_pipeline():
    """
    Orchestrates the full GL Mapping pipeline.
    """

    print("\n🚀 GL Mapping Pipeline Started\n")

    try:
        # Ensure output folder exists
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Stage 1: Load data
        bank_df, rules_df, coa_df = load_data()

        # Stage 2: Parse rules
        parsed_rules = parse_rule_stage(rules_df)

        # Stage 3: Apply rules
        mapped_transactions = rule_engine_stage(bank_df, parsed_rules)

        # Stage 4: COA enrichment
        enriched_transactions = coa_enrichment_stage(
            mapped_transactions,
            coa_df,
        )

        # Stage 5: Validation
        validation_stage(enriched_transactions)

        # Stage 6: Trial balance
        trial_balance_df = trial_balance_stage(enriched_transactions)

        # Stage 7: P&L
        pnl_stage(trial_balance_df)

    except Exception as e:
        print("\n❌ PIPELINE FAILED")
        print(f"Error: {str(e)}")


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    run_pipeline()