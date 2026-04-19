# Overview

## What this is

A live, interactive analytics platform for Polymarket binary prediction
markets — built in Marimo so any analyst can explore the data without
touching code.

## Quickstart

```bash
git clone <your-repo>
cd DATAHACKS2026
pip install -r requirements.txt
pip install marimo scipy sphinx sphinx-rtd-theme myst-parser
marimo run analytics.py
```

Navigate to `http://localhost:2718`.

## What you can do

- **Section 1** — See where crowds misprice YES tokens across a market's life
- **Section 2** — Find arbitrage windows by asset, interval, and hour of day
- **Section 3** — Test whether order book pressure predicts outcomes
- **Section 4** — Compare strategy edge across volatility regimes
- **Section 7** — Tune strategy parameters live and watch the equity curve update

## Data sources

| Source | Contents |
|---|---|
| `polymarket.db` | YES/NO prices, Chainlink oracle |
| `polymarket_books/` | Full order book depth |
| `binance_lob/` | Binance 20-level LOB at 100ms |
