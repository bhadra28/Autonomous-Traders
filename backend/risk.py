"""Pre-trade risk guardrails, enforced in the accounts layer.

Every buy and sell passes through these checks before it touches the account, so a
trader agent cannot bypass them however it is prompted. A rejected trade raises
RiskLimitError with a message that tells the agent the largest trade it may make,
so it can resize and try again instead of giving up.

Limits are read from the environment:
    RISK_ENABLED              true/false, default true
    RISK_MAX_POSITION_PCT     max share of portfolio value in one symbol, default 0.30
    RISK_MAX_TRADE_PCT        max share of portfolio value in one trade, default 0.20
    RISK_MAX_TRADES_PER_DAY   max buys and sells per trader per day, default 10
"""

import math
import os
from dataclasses import dataclass, asdict
from datetime import datetime

from dotenv import load_dotenv

load_dotenv(override=True)


class RiskLimitError(ValueError):
    """A trade that breaks a risk limit."""


@dataclass(frozen=True)
class RiskLimits:
    enabled: bool = True
    max_position_pct: float = 0.30
    max_trade_pct: float = 0.20
    max_trades_per_day: int = 10

    @classmethod
    def from_env(cls) -> "RiskLimits":
        return cls(
            enabled=os.getenv("RISK_ENABLED", "true").strip().lower() == "true",
            max_position_pct=float(os.getenv("RISK_MAX_POSITION_PCT", cls.max_position_pct)),
            max_trade_pct=float(os.getenv("RISK_MAX_TRADE_PCT", cls.max_trade_pct)),
            max_trades_per_day=int(os.getenv("RISK_MAX_TRADES_PER_DAY", cls.max_trades_per_day)),
        )

    def describe(self) -> dict:
        return asdict(self)


def check_quantity(quantity: int) -> None:
    """Reject zero or negative quantities, which would otherwise move cash the wrong way."""
    if not isinstance(quantity, int) or quantity <= 0:
        raise RiskLimitError(f"Quantity must be a positive whole number of shares, got {quantity}.")


def trades_today(timestamps: list[str], today: str | None = None) -> int:
    """Count transactions whose 'YYYY-MM-DD HH:MM:SS' timestamp falls on today."""
    today = today or datetime.now().strftime("%Y-%m-%d")
    return sum(1 for ts in timestamps if ts.startswith(today))


def check_daily_limit(limits: RiskLimits, timestamps: list[str]) -> None:
    count = trades_today(timestamps)
    if count >= limits.max_trades_per_day:
        raise RiskLimitError(
            f"Daily trade limit reached: {count} of {limits.max_trades_per_day} trades already made today. "
            "No more trades are allowed until tomorrow."
        )


def max_buy_quantity(limits: RiskLimits, price: float, held: int, portfolio_value: float, cash: float) -> int:
    """The largest number of shares that fits every limit and the available cash."""
    if price <= 0:
        return 0
    by_trade = limits.max_trade_pct * portfolio_value / price
    by_position = limits.max_position_pct * portfolio_value / price - held
    by_cash = cash / price
    return max(0, math.floor(min(by_trade, by_position, by_cash)))


def check_buy(
    limits: RiskLimits,
    symbol: str,
    quantity: int,
    price: float,
    held: int,
    portfolio_value: float,
    cash: float,
    timestamps: list[str],
) -> None:
    """Raise RiskLimitError if buying `quantity` shares of `symbol` at `price` breaks a limit."""
    check_quantity(quantity)
    if not limits.enabled:
        return
    check_daily_limit(limits, timestamps)

    trade_value = quantity * price
    position_value = (held + quantity) * price
    allowed = max_buy_quantity(limits, price, held, portfolio_value, cash)
    hint = f"The most you can buy of {symbol} right now is {allowed} shares."

    if trade_value > limits.max_trade_pct * portfolio_value:
        raise RiskLimitError(
            f"Trade too large: buying {quantity} {symbol} is ${trade_value:,.0f}, "
            f"over the {limits.max_trade_pct:.0%} per-trade limit (${limits.max_trade_pct * portfolio_value:,.0f}). {hint}"
        )
    if position_value > limits.max_position_pct * portfolio_value:
        raise RiskLimitError(
            f"Position too concentrated: {symbol} would be ${position_value:,.0f}, "
            f"over the {limits.max_position_pct:.0%} per-position limit (${limits.max_position_pct * portfolio_value:,.0f}). {hint}"
        )


def check_sell(limits: RiskLimits, quantity: int, timestamps: list[str]) -> None:
    """Sells reduce risk, so only the quantity and daily trade count are checked."""
    check_quantity(quantity)
    if limits.enabled:
        check_daily_limit(limits, timestamps)
