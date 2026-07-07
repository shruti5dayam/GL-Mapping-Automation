"""
rule_parser.py

Parses Bank Feed Rules into structured Python dictionaries.

Responsibilities
----------------
- Parse Rule Conditions JSON
- Parse Rule Outputs JSON
- Extract transaction direction (Deposit / Payment)
- Extract searchable keywords
- Preserve AND / OR rule logic
- Extract mapped Account Name

Author: Shruti GL Mapping Project
"""

import json


def load_json(json_string: str) -> dict:
    """
    Safely convert a JSON string into a Python dictionary.

    Parameters
    ----------
    json_string : str
        JSON stored as text inside Excel.

    Returns
    -------
    dict
        Parsed JSON dictionary.
    """

    if not json_string:
        return {}

    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return {}


def parse_rule(rule_row: dict) -> dict:
    """
    Parse one Bank Feed Rule.

    Parameters
    ----------
    rule_row : dict

    Returns
    -------
    dict
        Structured rule.
    """

    conditions_json = load_json(rule_row["Rule Conditions"])
    outputs_json = load_json(rule_row["Rule Outputs"])

    keywords = []
    transaction_type = None

    rule_conditions = conditions_json.get("ruleConditions", [])

    for condition in rule_conditions:

        rule_type = condition.get("ruleType")
        value = str(condition.get("value", "")).strip()

        # -----------------------------------
        # Transaction Direction
        # ruleType = 10
        #  1  -> Deposit
        # -1  -> Payment
        # -----------------------------------
        if rule_type == 10:

            try:
                transaction_type = int(value)
            except ValueError:
                transaction_type = None

            continue

        # -----------------------------------
        # Text matching conditions
        # ruleType 0,1,6 are searchable text
        # -----------------------------------
        if rule_type in (0, 1, 6):

            if value:
                keywords.append(value)

    account_name = ""

    for action in outputs_json.get("ruleActions", []):

        if action.get("actionType") == 0:

            account_name = str(
                action.get("value", "")
            ).strip()

            break

    return {
        "rule_name": rule_row["Rule Name"],
        "transaction_type": transaction_type,
        "is_and_rule": conditions_json.get("isAndRule", True),
        "keywords": keywords,
        "account_name": account_name,
    }


def parse_rules(rules_df):
    """
    Parse every Bank Feed Rule.

    Parameters
    ----------
    rules_df : pd.DataFrame

    Returns
    -------
    list
        List of parsed rules.
    """

    parsed_rules = []

    for _, row in rules_df.iterrows():
        parsed_rules.append(parse_rule(row))

    return parsed_rules