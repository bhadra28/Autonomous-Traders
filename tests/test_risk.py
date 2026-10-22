from datetime import datetime

import pytest

from backend.risk import RiskLimits, RiskLimitError, check_buy, check_sell, max_buy_quantity, trades_today

LIMITS = RiskLimits(enabled=True, max_position_pct=0.30, max_trade_pct=0.20, max_trades_per_day=3)


def buy(quantity, price=100.0, held=0, value=10_000.0, cash=10_000.0, timestamps=()):
    check_buy(LIMITS, "AAPL", quantity, price, held, value, cash, list(timestamps))


def test_buy_within_limits_passes():
    buy(20)  # $2,000 is exactly the 20% trade limit


def test_trade_over_size_limit_is_blocked_with_allowed_quantity():
    with pytest.raises(RiskLimitError, match="Trade too large") as e:
        buy(21)
    assert "20 shares" in str(e.value)


def test_position_over_concentration_limit_is_blocked():
    # Already holding $2,500 of AAPL, so another $1,000 would make it 35% of the portfolio.
    with pytest.raises(RiskLimitError, match="too concentrated") as e:
        buy(10, held=25)
    assert "5 shares" in str(e.value)


@pytest.mark.parametrize("quantity", [0, -5])
def test_zero_and_negative_quantities_are_rejected(quantity):
    with pytest.raises(RiskLimitError, match="positive"):
        buy(quantity)
    with pytest.raises(RiskLimitError, match="positive"):
        check_sell(LIMITS, quantity, [])


def test_daily_trade_limit_blocks_buys_and_sells():
    stamp = datetime.now().strftime("%Y-%m-%d 10:00:00")
    with pytest.raises(RiskLimitError, match="Daily trade limit"):
        buy(1, timestamps=[stamp] * 3)
    with pytest.raises(RiskLimitError, match="Daily trade limit"):
        check_sell(LIMITS, 1, [stamp] * 3)


def test_trades_on_other_days_do_not_count():
    assert trades_today(["2020-01-01 10:00:00", "2026-10-22 09:00:00"], today="2026-10-22") == 1


def test_disabled_limits_still_reject_bad_quantities():
    off = RiskLimits(enabled=False)
    check_buy(off, "AAPL", 1_000, 100.0, 0, 10_000.0, 1_000_000.0, [])
    with pytest.raises(RiskLimitError):
        check_buy(off, "AAPL", -1, 100.0, 0, 10_000.0, 10_000.0, [])


def test_max_buy_quantity_respects_cash():
    assert max_buy_quantity(LIMITS, price=100.0, held=0, portfolio_value=10_000.0, cash=500.0) == 5


def test_limits_read_from_environment(monkeypatch):
    monkeypatch.setenv("RISK_MAX_TRADE_PCT", "0.05")
    monkeypatch.setenv("RISK_ENABLED", "false")
    limits = RiskLimits.from_env()
    assert limits.max_trade_pct == 0.05
    assert limits.enabled is False
