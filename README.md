# AlphaSee

**We don’t predict the market — we wait for it to agree with itself.**

AlphaSee is a full-stack trading system built for DATAHACKS 2026. It combines a multi-signal quantitative strategy, a backtesting engine, and interactive analytics tools to trade BTC/ETH/SOL binary prediction markets.

---

## 👥 Team

* Antara
* Sourish
* Jayani
* Diana

---

## ⚡ Quickstart (Everything)

```bash
# Clone your repo
git clone https://github.com/antara-chhabra/DATAHACKS2026
cd DATAHACKS2026

# Install core dependencies
pip install -r requirements.txt

# Install analytics (Marimo) + extras
pip install marimo numpy pandas scipy pyarrow matplotlib

# Download data (~1.3 GB)
python download_data.py
```

---

### ▶️ Run Backtests

```bash
python run_backtest.py aggressive_edge.py
python run_backtest.py aggressive_edge.py --data data/validation/
```

---

### 🖥️ Run Dashboard (AlphaSee)

```bash
cd alphasee
npm install
npm run dev
# http://localhost:3000
```

---

### 📊 Run Analytics App (Marimo)

```bash
# from repo root
marimo run analytics.py --port 2718
# http://localhost:2718
```

---

## 🚀 Results

| Window      | Return      | Sharpe | Win Rate | Max DD |
| ----------- | ----------- | ------ | -------- | ------ |
| 20h         | +23.3%      | 47.82  | 83.3%    | 3.6%   |
| 40h         | +25.0%      | 32.67  | 84.6%    | 3.6%   |
| 80h         | +26.6%      | 15.82  | 83.3%    | 11.5%  |
| 160h        | +56.2%      | 7.64   | 70.8%    | 50.1%  |
| Full (178h) | **+109.4%** | 11.94  | 72.2%    | 39.2%  |
| Validation  | +23.0%      | 16.36  | 48.6%    | 15.3%  |

---

## 🧠 Strategy — `AggressiveEdgeV3`

Implemented in `aggressive_edge.py`, combining **arbitrage + directional signals**. This file is located in strategies.

### Arbitrage

* Trigger: `YES ask + NO ask < $1`
* Action: buy both sides → guaranteed profit

### Directional (BTC + ETH only)

Uses 4-signal confirmation:

* Chainlink price drift
* Binance momentum
* Market mispricing
* Cross-asset agreement

### Key Parameters

```python
arb_edge = 0.006
min_edge = 0.045
momentum_threshold = 0.0002
cash_frac = 0.92
MAX_STALE_S = 30
```

---

## 🖥️ AlphaSee Dashboard

Interactive Next.js app in `alphasee/`.

Features:

* Decision Engine (toggle signals live)
* Strategy rationale (data → decisions)
* Asset-level performance
* Time-series charts
* 3D volatility surface
* Correlation + environmental insights

---

## 📊 Analytics (Marimo)

`analytics.py` provides:

* Fair value modeling (Black-Scholes-style)
* Arbitrage detection across 8k+ markets
* Order book + pricing bias visualization

We also built an extended version of this analytics pipeline integrating external APIs:

🔗 https://github.com/dianazhu9879/DATAHACKS2026

---

## 📁 Project Structure

```
DATAHACKS2026/
├── my_strategy.py
├── max_pnl_hybrid.py
├── analytics.py
├── run_backtest.py
├── download_data.py
├── results/
├── alphasee/
├── backtester/
├── notebooks/
├── tests/
└── docs/
```

---

# 📘 Economics Track Directions

## DATAHACKS 2026 - BTC/ETH/SOL Prediction Market Hackathon

Build a trading strategy for binary prediction markets on BTC, ETH, and SOL price direction. Your algorithm trades YES/NO tokens across 5-minute, 15-minute, and hourly markets, buying when you think the market is mispriced and selling when you have an edge.

Starting capital: $10,000
Scoring: total P&L (primary), Sharpe ratio (tiebreaker) - see docs/SCORING.md
Submission: one .py file (details TBD - organizer will announce)

---

## Quickstart

```bash
git clone https://github.com/austntatious/DATAHACKS2026
cd DATAHACKS2026
pip install -r requirements.txt

# Download the training and validation data (~1.3 GB total)
python download_data.py

# Copy the template and start coding
cp strategy_template.py my_strategy.py
# ...edit my_strategy.py...

# Run your strategy on training data
python run_backtest.py my_strategy.py

# Evaluate on held-out validation data
python run_backtest.py my_strategy.py --data data/validation/
```

Both backtest commands print a BACKTEST REPORT block with P&L, Sharpe ratio, max drawdown, trade count, and the Competition Score (= total P&L).

---

## Pick your scope - one market, one asset, or all of them

This is a strategic design choice, not a constraint. You can build:

* A specialist - e.g. "only 5-minute BTC markets"
* A multi-asset directional bot
* A generalist across all markets

```python
def on_tick(self, state: MarketState) -> list[Order]:
    for slug, market in state.markets.items():
        if market.interval != "5m":
            continue
        if not slug.startswith("btc-"):
            continue
```

---

## Speeding up your dev loop

```bash
python run_backtest.py my_strategy.py --hours 4
python run_backtest.py my_strategy.py --assets BTC
python run_backtest.py my_strategy.py --intervals 5m
```

Always validate unfiltered:

```bash
python run_backtest.py my_strategy.py --data data/validation/
```

---

## How the markets work

* YES pays $1 if price increases
* NO pays $1 if price decreases
* YES + NO ≈ $1 → arbitrage opportunity

---

## Rules (Summary)

* $10,000 starting cash
* 500 share cap per market
* No short selling
* T+1 latency

Full rules: docs/RULES.md

---

## License

MIT
