"""Performance metrics for a trader's account.

The functions take plain lists so they are easy to test; performance() puts them
together for one account. Returns and drawdowns are fractions (0.05 means 5%).
"""

import statistics


def period_returns(values: list[float]) -> list[float]:
    """Return between each consecutive pair of portfolio values."""
    return [(b - a) / a for a, b in zip(values, values[1:]) if a]


def max_drawdown(values: list[float]) -> float:
    """Largest peak-to-trough fall, as a positive fraction of the peak."""
    peak, worst = float("-inf"), 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def volatility(values: list[float]) -> float:
    """Standard deviation of period returns; 0 when there are too few points."""
    returns = period_returns(values)
    return statistics.stdev(returns) if len(returns) >= 2 else 0.0


def realized_pnl(transactions: list[tuple[str, int, float]]) -> float:
    """Profit locked in by sells, using average cost. Each item is (symbol, quantity, price); sells are negative."""
    shares: dict[str, int] = {}
    cost: dict[str, float] = {}
    realized = 0.0
    for symbol, quantity, price in transactions:
        if quantity > 0:
            shares[symbol] = shares.get(symbol, 0) + quantity
            cost[symbol] = cost.get(symbol, 0.0) + quantity * price
        elif quantity < 0 and shares.get(symbol):
            sold = min(-quantity, shares[symbol])
            avg = cost[symbol] / shares[symbol]
            realized += sold * (price - avg)
            shares[symbol] -= sold
            cost[symbol] -= sold * avg
    return realized


def performance(account, current_value: float, initial_balance: float, blocked_trades: int = 0) -> dict:
    """Headline metrics for one account, rounded for display."""
    values = [initial_balance] + [value for _, value in account.portfolio_value_time_series] + [current_value]
    buys = sum(1 for t in account.transactions if t.quantity > 0)
    sells = sum(1 for t in account.transactions if t.quantity < 0)
    return {
        "portfolio_value": round(current_value, 2),
        "total_return_pct": round((current_value - initial_balance) / initial_balance * 100, 2),
        "max_drawdown_pct": round(max_drawdown(values) * 100, 2),
        "volatility_pct": round(volatility(values) * 100, 2),
        "realized_pnl": round(realized_pnl([(t.symbol, t.quantity, t.price) for t in account.transactions]), 2),
        "buys": buys,
        "sells": sells,
        "blocked_trades": blocked_trades,
    }
