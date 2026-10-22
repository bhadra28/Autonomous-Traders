import pytest

from backend.metrics import max_drawdown, period_returns, realized_pnl, volatility


def test_period_returns():
    assert period_returns([100, 110, 99]) == pytest.approx([0.10, -0.10])


def test_max_drawdown_measures_peak_to_trough():
    # Peak 120, trough 90: a 25% drawdown, even though it later recovers.
    assert max_drawdown([100, 120, 90, 130]) == pytest.approx(0.25)


def test_max_drawdown_is_zero_when_only_rising():
    assert max_drawdown([100, 101, 105]) == 0.0


def test_volatility_needs_at_least_two_returns():
    assert volatility([100, 110]) == 0.0
    assert volatility([100, 110, 99]) > 0


def test_realized_pnl_uses_average_cost():
    # Buy 10 at $100 and 10 at $120 (avg $110), then sell 5 at $130: 5 * $20 profit.
    trades = [("AAPL", 10, 100.0), ("AAPL", 10, 120.0), ("AAPL", -5, 130.0)]
    assert realized_pnl(trades) == pytest.approx(100.0)


def test_realized_pnl_ignores_unmatched_sells():
    assert realized_pnl([("AAPL", -5, 130.0)]) == 0.0
