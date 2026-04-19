# AlphaSee — DATAHACKS 2026 Strategy Dashboard

**AlphaSee** is the interactive analytics dashboard for our DATAHACKS 2026 prediction-market trading strategy. It visualises every layer of the strategy — from raw data insights to cross-asset correlation signals — and ships with full dark/light mode support, an animated coin background, a live Black-Scholes probability engine, and an integrated Marimo analytics app.

---

## Running Everything Locally

There are **two servers** to start: the Next.js dashboard and the Marimo analytics app. Open two terminal tabs.

### Requirements

| Tool | Version |
|------|---------|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| Python | ≥ 3.10 |
| pip | any recent |

---

### 1 — Next.js Dashboard (AlphaSee UI)

```bash
# from the repo root
cd alphasee
npm install        # first time only
npm run dev
```

| URL | What you see |
|-----|--------------|
| http://localhost:3000 | Landing page |
| http://localhost:3000/dashboard | Full strategy dashboard |

The dev server hot-reloads on every file save. Use **◑ Dark Mode** in the bottom-right to toggle themes.

**Production build** (optional):

```bash
npm run build
npm start
```

---

### 2 — Marimo Analytics App

The Marimo app (`analytics.py`) is Jayani's interactive notebook — it connects to the live Polymarket data and runs the full EDA, Black-Scholes fair-value analysis, and arbitrage edge detection reactively in the browser.

```bash
# from the repo root (not alphasee/)
pip install marimo numpy pandas scipy pyarrow matplotlib
marimo run analytics.py --port 2718
```

Open **http://localhost:2718** — or click the **"Try it on Marimo / Sphinx"** button on the dashboard, which points there automatically.

> **Note:** The Marimo app expects data at `data/train/` by default. If you haven't downloaded the data yet, run `python download_data.py` first. You can also point it at a different directory using the configuration input inside the app.

---

### 3 — Python Backtester (strategy engine)

```bash
# from the repo root
pip install -r requirements.txt

# download training + validation data (~1.3 GB)
python download_data.py

# run the strategy
python run_backtest.py my_strategy.py

# validate on held-out data
python run_backtest.py my_strategy.py --data data/validation/
```

---

### Quick-start (all three together)

```bash
# Terminal 1 — dashboard
cd alphasee && npm run dev

# Terminal 2 — Marimo app
marimo run analytics.py --port 2718

# Terminal 3 — backtester (optional, run as needed)
python run_backtest.py my_strategy.py --hours 4 --assets BTC
```

---

## Dashboard Components

| Component | Description |
|-----------|-------------|
| **Decision Engine** | Toggle each of the 4 signals (Real Price, Momentum, Market Odds, Cross-Asset Agreement) to see how alignment drives the trade recommendation |
| **Why This Strategy?** | Core strategy pillars explaining why multi-signal confirmation outperforms single-signal entries |
| **EDA — Exploratory Data Analysis** | Clickable table of raw Polymarket order book insights — spread, pricing bias, order book depth, volatility σ, tick frequency — across BTC, ETH, SOL; click any row to expand the insight |
| **Strategy Rationale** | Step-by-step reasoning linking each data observation to a design decision in the strategy code |
| **Assets** | Per-asset 80h P&L, Sharpe ratio, and win-rate cards with expandable detail panels |
| **3D Volatility Surface** | Plotly.js surface plot of implied vol across strike × time for BTC, ETH, and SOL; tabs to switch assets |
| **Market Signals** | YES/NO price bars per interval with edge detection and hover tooltips |
| **Probability Engine** | Live Black-Scholes calculator mirroring `my_strategy.py` exactly — drag sliders to set BTC drift, market price, and time remaining; see fair P(YES), edge Δ, and the BUY/NO TRADE signal update in real time |
| **Performance & Analysis** | Strategy growth over time (20h/40h/80h/160h windows) + per-asset return comparison |
| **Environment, Energy & Climate** | BTC and ETH energy consumption vs. price area charts; clickable insight boxes; mock energy-adjusted strategy return graph |
| **Correlation & Market Environment** | Two-tab section — (1) Energy & Macro: scatter plot of energy price vs. crypto vol + exposure-adjustment chart; (2) Cross-Market: rolling correlation matrix and time series for BTC↔ETH, BTC↔Energy, ETH↔Energy |
| **Insights** | Six key quantitative findings from the backtest with stat callouts and tags |
| **Try it on Marimo / Sphinx** | CTA button that opens the live Marimo app at http://localhost:2718 |

---

## Tech Stack

| Layer | Library / Tool |
|-------|----------------|
| Framework | Next.js 16 (App Router, Turbopack) |
| Language | TypeScript |
| Styling | CSS Modules + Tailwind v4 + CSS custom properties |
| Line/Area/Scatter charts | Recharts |
| 3D Volatility chart | Plotly.js via `react-plotly.js` (SSR-disabled) |
| Background animation | Canvas API — falling coin rain |
| Landing animation | CSS keyframes — floating coin images |
| Theme system | React Context (`ThemeContext`) + `data-theme` on `<html>` |
| Fonts | Google Fonts — Roboto + Roboto Mono |
| Marimo app | marimo 0.23.1 + pandas + matplotlib |
| Python backtester | numpy, pandas, scipy, pyarrow |

---

## Project Structure

```
alphasee/
├── app/
│   ├── globals.css              # Light & dark mode CSS variables
│   ├── ThemeContext.tsx         # Theme provider + useTheme hook
│   ├── layout.tsx               # Root layout — wraps ThemeProvider + ThemeToggle
│   ├── page.tsx                 # Landing page (animated coins, stat chips)
│   ├── page.module.css
│   └── dashboard/
│       ├── page.tsx             # Dashboard — all components assembled
│       └── dashboard.module.css
├── components/
│   ├── ThemeToggle.tsx          # Floating dark/light mode pill button
│   ├── FallingCoins.tsx         # Canvas-based animated BTC/ETH/SOL coin rain
│   ├── DecisionEngine.tsx       # Interactive 4-signal panel
│   ├── WhyStrategy.tsx          # Strategy pillars
│   ├── EDA.tsx                  # Exploratory Data Analysis clickable table
│   ├── StrategyBox.tsx          # Strategy rationale (data → decision steps)
│   ├── Assets.tsx               # Per-coin stat cards with detail expand
│   ├── Volatility3D.tsx         # 3D Plotly volatility surface (BTC/ETH/SOL)
│   ├── MarketSignals.tsx        # YES/NO price bars per interval
│   ├── ProbabilityEngine.tsx    # Live Black-Scholes probability calculator
│   ├── Charts.tsx               # Strategy growth + performance charts
│   ├── EnvironmentalImpact.tsx  # Energy consumption charts + insight boxes
│   ├── CorrelationSignals.tsx   # Energy/macro & cross-market correlation
│   └── Insights.tsx             # Key quantitative findings
└── public/
    ├── btc.svg / eth.svg / sol.svg
    └── timeseries.json          # Strategy P&L time series data
```

---

## Dark Mode

Every component uses only CSS custom properties — no hardcoded hex colors. The `data-theme="dark"` attribute on `<html>` switches the full palette in one step.

Toggle with the **◑ Dark Mode** / **☀ Light Mode** pill in the bottom-right corner. The choice is saved to `localStorage` and restored on the next visit.

---

## Marimo Integration

`analytics.py` (authored by Jayani) is a fully reactive Marimo notebook. It connects to the Polymarket SQLite database and runs:

- Full EDA on 8,466 binary markets
- Black-Scholes fair-value computation per tick (mirrors `my_strategy.py`)
- Arbitrage edge detection (YES + NO ask sum analysis)
- Chainlink oracle vs. Binance mid-price comparison
- Outcome win-rate breakdowns per asset and interval

Run it with `marimo run analytics.py --port 2718` and open http://localhost:2718, or click the button on the dashboard.

---

## Environment & Climate Angle

- **BTC energy chart** — mining consumption tracks price cycles; high-energy periods correlate with elevated σ and wider spreads that our strategy exploits
- **ETH post-Merge chart** — 99.95% energy drop permanently changed ETH's volatility profile; strategy adapts by treating post-Merge ETH momentum as a more reliable confirming signal
- **Clickable insight boxes** on each chart explain the strategy-level implication
- **Correlation panels** show how macro energy signals feed into position-sizing filters

---

## License

MIT — see [`../LICENSE`](../LICENSE).
