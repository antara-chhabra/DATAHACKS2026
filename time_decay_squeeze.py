"""
Strategy 3 (12pm) — Time-Decay Binary Squeeze
In the final seconds before settlement, a binary prediction market's price must
converge to either $0 or $1. Markets with 30–60 seconds remaining frequently
remain mispriced at 0.60–0.85 for the winning side — offering easy upside as
prices march toward $1 over the remaining ticks.
Logic:
  1. Track Chainlink BTC open price on first tick per market.
  2. Only act when time_remaining_s <= entry_window (default 60s).
  3. Determine the winning side: chainlink_current > open → YES winning; else NO.
  4. Buy the winning side if its ask is still below price_ceiling (default 0.88).
     The gap between ask and $1.00 is the expected profit per share.
  5. Enter only once per market to avoid stacking risk near expiry.
Applied to BTC markets only (state.chainlink_btc is the settlement reference).
For non-BTC markets falls back to the market's own YES price as a proxy:
if yes_price > 0.55 the market itself implies YES is currently winning.
"""

from __future__ import annotations

from backtester.strategy import BaseStrategy, MarketState, Order, Settlement, Side, Token


def _is_btc_market(slug: str) -> bool:
    s = slug.lower()
    return s.startswith("btc-") or s.startswith("bitcoin-")


class TimeDecaySqueeze(BaseStrategy):
    """
    Enters the currently-winning side in the final seconds before settlement.

    Parameters
    ----------
    entry_window : float
        Seconds before expiry to start looking for entries (default 60).
    price_ceiling : float
        Maximum ask price to pay for the winning side — ensures minimum edge
        of (1.0 - price_ceiling) per share at settlement (default 0.88).
    size : float
        Shares per order (default 50). Larger than other strategies because
        the holding period is short and the signal is high-conviction.
    """

    def __init__(
        self,
        entry_window: float = 60.0,
        price_ceiling: float = 0.88,
        size: float = 50.0,
    ):
        self.entry_window = entry_window
        self.price_ceiling = price_ceiling
        self.size = size
        self._open_chainlink: dict[str, float] = {}
        self._entered: set[str] = set()

    def on_tick(self, state: MarketState) -> list[Order]:
        orders: list[Order] = []
        cl_now = state.chainlink_btc
        for slug, market in state.markets.items():
            if slug not in self._open_chainlink:
                if cl_now and cl_now > 0 and _is_btc_market(slug):
                    self._open_chainlink[slug] = cl_now
                else:
                    self._open_chainlink[slug] = 0.0

            if market.time_remaining_s > self.entry_window:
                continue
            if slug in self._entered:
                continue

            cl_open = self._open_chainlink[slug]
            is_btc = _is_btc_market(slug)

            if is_btc and cl_open > 0:
                yes_winning = cl_now > cl_open
                no_winning = cl_now < cl_open
            else:
                yes_winning = market.yes_price > 0.55
                no_winning = market.no_price > 0.55

            if yes_winning:
                ask = market.yes_ask
                if ask <= 0 or ask >= self.price_ceiling:
                    continue
                cost = self.size * ask
                if cost > state.cash:
                    continue
                pos = state.positions.get(slug)
                if pos and pos.yes_shares + self.size > 500:
                    continue
                orders.append(
                    Order(
                        market_slug=slug,
                        token=Token.YES,
                        side=Side.BUY,
                        size=self.size,
                        limit_price=ask,
                    )
                )
                self._entered.add(slug)
            elif no_winning:
                ask = market.no_ask
                if ask <= 0 or ask >= self.price_ceiling:
                    continue
                cost = self.size * ask
                if cost > state.cash:
                    continue
                pos = state.positions.get(slug)
                if pos and pos.no_shares + self.size > 500:
                    continue
                orders.append(
                    Order(
                        market_slug=slug,
                        token=Token.NO,
                        side=Side.BUY,
                        size=self.size,
                        limit_price=ask,
                    )
                )
                self._entered.add(slug)
        return orders

    def on_settlement(self, settlement: Settlement) -> None:
        self._open_chainlink.pop(settlement.market_slug, None)
        self._entered.discard(settlement.market_slug)
