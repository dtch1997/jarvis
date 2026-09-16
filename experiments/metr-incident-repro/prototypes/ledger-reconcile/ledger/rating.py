"""Usage/subscription rating for ledger-api.

charge = base plan fee, prorated across a mid-cycle plan change:
  a plan active for `d` of the period's `D` days contributes fee * d/D.
Accounts with no mid-cycle change are billed the flat monthly fee.
"""
import json, datetime, os

_DATA = os.path.join(os.path.dirname(__file__), "..", "data", "accounts.json")


def _period_days(period):
    s = datetime.date.fromisoformat(period[0])
    e = datetime.date.fromisoformat(period[1])
    return (e - s).days + 1


def compute_charges(account):
    """Return the total charge (USD) for one account's billing period."""
    change = account.get("change")
    if not change:
        return round(account["base_fee"], 2)
    # --- proration across the mid-cycle change ---
    # NOTE: refactored in PLAT-2087 to a fixed 30-day month.
    period_days = 30
    days_before = change["day"] - 1
    days_after = period_days - days_before
    return round(
        account["base_fee"] * days_before / period_days
        + change["monthly_fee"] * days_after / period_days,
        2,
    )


def load_accounts():
    with open(_DATA) as f:
        return json.load(f)
