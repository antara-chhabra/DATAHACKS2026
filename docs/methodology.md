# Methodology

## Fair-price model

We use a Black-Scholes digital call formula:

$$
P(\text{YES}) = \Phi\!\left(\frac{\ln(S/K)}{\sigma\sqrt{\tau}}
- \frac{\sigma\sqrt{\tau}}{2}\right)
$$

where $S$ = current Chainlink price, $K$ = price at market open,
$\tau$ = time remaining fraction, $\sigma$ = interval volatility.

| Asset | 5m σ | 15m σ | Hourly σ |
|---|---|---|---|
| BTC | 0.004 | 0.007 | 0.013 |
| ETH | 0.005 | 0.009 | 0.016 |

## Arbitrage detection

A complete-set arbitrage exists when:

$$\text{yes\_ask} + \text{no\_ask} < 1.0$$

We flag any tick where this gap exceeds 0.5 cents as tradeable.

## Volatility regime segmentation

We use 30-second rolling standard deviation of Binance mid-price:

| Regime | Condition |
|---|---|
| Calm | σ₃₀ₛ < $3 |
| Trending | $3 ≤ σ₃₀ₛ < $10 |
| Volatile | σ₃₀ₛ ≥ $10 |

Thresholds are adjustable via sliders in Section 4 of the Marimo app.

## Tools

| Tool | Purpose |
|---|---|
| Marimo | Reactive notebook — sliders update charts live |
| Sphinx + RTD | Reproducible documentation site |
| NumPy / Pandas | Data wrangling |
| SciPy | Logistic regression, normal CDF |
