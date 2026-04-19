"""
Fair Value — Black-Scholes model adapted from appendix/btc_fair_value_estimator.py.

Computes P(YES) = N(d2) using realized volatility and trades when the market
price diverges from the model price by more than a threshold.
"""

import math

from backtester.strategy import BaseStrategy, Fill, MarketState, Order, Side, Token


def _standard_normal_cdf(x: float) -> float:
    """Approximate Phi(x) using the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _compute_fair_prob(
    btc_current: float,
    btc_open: float,
    vol_15m: float,
    time_remaining_frac: float,
) -> float:
    """Compute Black-Scholes P(YES) = N(d2)."""
    if btc_open <= 0 or btc_current <= 0:
        return 0.5

    tau = max(time_remaining_frac, 0.001)
    sigma = vol_15m if vol_15m > 0 else 0.005
    sigma_sqrt_tau = sigma * math.sqrt(tau)

    if sigma_sqrt_tau < 1e-8:
        return 0.99 if btc_current >= btc_open else 0.01

    log_moneyness = math.log(btc_current / btc_open)
    d2 = log_moneyness / sigma_sqrt_tau - sigma_sqrt_tau / 2.0

    prob = _standard_normal_cdf(d2)
    return max(0.01, min(0.99, prob))


class FairValue(BaseStrategy):
    """
    Trade based on Black-Scholes fair value vs market price.

    Buys YES when market is cheap (fair > market + threshold).
    Buys NO when market is rich (fair < market - threshold).
    """

    def __init__(
        self,
        vol_15m: float = 0.005,  # ~0.5% 15-min vol (typical BTC)
        threshold: float = 0.08,  # trade when |fair - market| > 8 cents
        size: float = 30.0,
    ):
        self.vol_15m = vol_15m
        self.threshold = threshold
        self.size = size
        self._btc_open: dict[str, float] = {}  # slug -> open BTC price

    def on_tick(self, state: MarketState) -> list[Order]:
        orders = []

        if state.chainlink_btc <= 0:
            return orders

        for slug, market in state.markets.items():
            # Record BTC price at market start (first tick we see it)
            if slug not in self._btc_open:
                self._btc_open[slug] = state.chainlink_btc

            btc_open = self._btc_open[slug]
            fair = _compute_fair_prob(
                state.chainlink_btc, btc_open,
                self.vol_15m, market.time_remaining_frac,
            )
            market_mid = market.yes_price

            if market_mid <= 0:
                continue

            delta = fair - market_mid

            if delta > self.threshold and market.yes_ask > 0:
                # Market is cheap — buy YES
                if state.cash >= self.size * market.yes_ask:
                    orders.append(Order(
                        market_slug=slug,
                        token=Token.YES,
                        side=Side.BUY,
                        size=self.size,
                        limit_price=min(fair, market.yes_ask + 0.02),
                    ))

            elif delta < -self.threshold and market.no_ask > 0:
                # Market is rich — buy NO
                if state.cash >= self.size * market.no_ask:
                    orders.append(Order(
                        market_slug=slug,
                        token=Token.NO,
                        side=Side.BUY,
                        size=self.size,
                        limit_price=min(1 - fair, market.no_ask + 0.02),
                    ))

        return orders
