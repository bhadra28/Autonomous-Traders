# Autonomous Traders

A simulated trading floor where four AI traders (Warren, George, Ray and Cathie), each with their own
strategy, research the market and buy and sell shares on their own. It's built with the
[OpenAI Agents SDK](https://github.com/openai/openai-agents-python) and the
[Model Context Protocol (MCP)](https://modelcontextprotocol.io).

## How it works

- **Trader agents** (`backend/traders.py`) decide what to trade. Each one uses a **researcher** agent as a tool.
- **MCP servers** (`backend/mcp_servers.py`) give the agents their tools:
  - `accounts_server`: our own server for balances, holdings, buying and selling
  - `market_server`: share prices (simulated, or real data from Massive when `MASSIVE_API_KEY` is set)
  - `push_server`: push notifications via Pushover
  - Fetch, Tavily web search and a libSQL memory server for the researcher
- **Scheduler** (`backend/trading_floor.py`) runs every trader every `RUN_EVERY_N_MINUTES`.
- **Dashboards**: a Gradio UI (`app.py` + `demo/`), or a FastAPI JSON API (`backend/api.py`) with a
  Vite/TypeScript frontend (`frontend/`).

## Risk guardrails and performance metrics

My addition to the course project: autonomous agents shouldn't be trusted to police themselves, so every
trade now passes pre-trade risk checks in the accounts layer, where no prompt can get around them.

- **Guardrails** (`backend/risk.py`): limits on position size (default 30% of portfolio value per symbol),
  trade size (20% per trade) and trades per day (10). Zero and negative quantities are rejected too. Before
  this, a negative "buy" would have *added* cash to an account.
- **Agents adapt instead of failing**: a blocked trade returns an error naming the largest allowed quantity,
  so the agent can resize and retry. Every block is logged (orange in the dashboard).
- **New MCP tools**: `get_risk_limits`, so agents can size trades up front, and `get_performance`
  (`backend/metrics.py`), which reports total return, max drawdown, volatility, realized P&L
  (average-cost method), trade counts and blocked trades.
- **Visible everywhere**: a metrics strip on each trader in the Gradio dashboard, plus
  `GET /api/risk-limits` and `GET /api/traders/{name}/performance`.
- **Tests**: a pytest suite for the limits, metrics and account integration, using a throwaway database.

Limits are set in `.env` (see `.env.example`). Run the tests with:

```bash
uv run pytest
```

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Python 3.12+, and Node.js (for `npx` MCP servers and the frontend).

```bash
uv sync
cp .env.example .env   # then add your keys
```

Set up the four traders' accounts and strategies:

```bash
uv run -m backend.reset
```

## Run

Start the trading floor (the agents):

```bash
uv run -m backend.trading_floor
```

Then, in a second terminal, open a dashboard. Gradio:

```bash
uv run app.py
```

Or the API plus web frontend:

```bash
uv run uvicorn backend.api:app --port 8000
cd frontend && npm install && npm run dev
```

## Credits

Based on the MCP week of Ed Donner's [Agents course](https://github.com/ed-donner/agents) (MIT License).
