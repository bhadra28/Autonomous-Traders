"""The guardrails as an agent meets them: through Account.buy_shares and sell_shares."""

import pytest

from backend.database import count_logs
from backend.risk import RiskLimitError


def test_normal_buy_goes_through(account):
    account.buy_shares("AAPL", 10, "fits strategy")
    assert account.holdings == {"AAPL": 10}
    assert account.balance < 10_000


def test_oversized_buy_is_blocked_and_logged(account):
    blocked_before = count_logs("tester", "risk")
    with pytest.raises(RiskLimitError, match="Trade too large"):
        account.buy_shares("AAPL", 50, "all in")  # $5,000 is 50% of the portfolio
    assert account.holdings == {}
    assert account.balance == 10_000
    assert count_logs("tester", "risk") == blocked_before + 1


def test_negative_buy_cannot_create_cash(account):
    with pytest.raises(RiskLimitError):
        account.buy_shares("AAPL", -10, "exploit")
    assert account.balance == 10_000


def test_daily_limit_applies_through_the_account(account, monkeypatch):
    monkeypatch.setenv("RISK_MAX_TRADES_PER_DAY", "2")
    account.buy_shares("AAPL", 1, "one")
    account.buy_shares("MSFT", 1, "two")
    with pytest.raises(RiskLimitError, match="Daily trade limit"):
        account.sell_shares("AAPL", 1, "three")


def test_performance_reports_trades_and_blocks(account):
    account.buy_shares("AAPL", 10, "buy")
    account.sell_shares("AAPL", 5, "trim")
    with pytest.raises(RiskLimitError):
        account.buy_shares("TSLA", 100, "too big")
    perf = account.get_performance()
    assert perf["buys"] == 1
    assert perf["sells"] == 1
    assert perf["blocked_trades"] >= 1
    # The spread on both legs means a small realized loss at flat prices.
    assert perf["realized_pnl"] < 0
    assert set(perf) >= {"total_return_pct", "max_drawdown_pct", "volatility_pct"}
