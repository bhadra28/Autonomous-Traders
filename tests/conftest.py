import os
import tempfile

import pytest

# Point the database at a throwaway file before any backend module is imported,
# so tests never touch the real accounts.db.
os.environ["ACCOUNTS_DB"] = os.path.join(tempfile.mkdtemp(), "test_accounts.db")

PRICES = {"AAPL": 100.0, "MSFT": 200.0, "TSLA": 50.0}


@pytest.fixture(autouse=True)
def default_limits(monkeypatch):
    """Pin the risk limits so a local .env can't change test results."""
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("RISK_MAX_POSITION_PCT", "0.30")
    monkeypatch.setenv("RISK_MAX_TRADE_PCT", "0.20")
    monkeypatch.setenv("RISK_MAX_TRADES_PER_DAY", "10")


@pytest.fixture
def account(monkeypatch):
    """A fresh $10,000 account with fixed share prices."""
    from backend import accounts

    monkeypatch.setattr(accounts, "get_share_price", lambda symbol: PRICES.get(symbol, 0.0))
    acct = accounts.Account.get("tester")
    acct.reset("test strategy")
    return acct
