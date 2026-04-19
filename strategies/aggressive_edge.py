"""
AggressiveEdge — settlement-consistent oracle + aggressive sizing.

Uses MarketView.chainlink_open (same definition as backtest settlements) for
fair value and direction. Per-asset Chainlink spot from MarketState. Falls back
to first-seen spot only if open is missing (rare).
"""

from __future__ import annotations

import math
from collections import deque

from backtester.strategy import (
    BaseStrategy,
    Fill,
    MarketState,
    MarketView,
    Order,
    Settlement,
    Side,
    Token,
)

_VOL = {
    ("BTC", "5m"): 0.0042,
    ("BTC", "15m"): 0.0075,
    ("BTC", "hourly"): 0.014,
    ("ETH", "5m"): 0.0060,
    ("ETH", "15m"): 0.010,
    ("ETH", "hourly"): 0.018,
    ("SOL", "5m"): 0.0095,
    ("SOL", "15m"): 0.016,
    ("SOL", "hourly"): 0.028,
}

_MAX_ENTRY = {
    "5m": 300,
    "15m": 380,
    "hourly": 450,
}

_MIN_BOOK_DEPTH = 40.0


def _asset_from_slug(slug: str) -> str:
    s = slug.lower()
    if s.startswith(("btc-", "bitcoin-")):
        return "BTC"
    if s.startswith(("eth-", "ethereum-")):
        return "ETH"
    return "SOL"


def _interval_from_slug(slug: str) -> str:
    s = slug.lower()
    if "-5m-" in s:
        return "5m"
    if "-15m-" in s:
        return "15m"
    return "hourly"


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _fair_prob(spot: float, spot_open: float, vol: float, frac: float) -> float:
    if spot_open <= 0 or spot <= 0:
        return 0.5
    tau = max(frac, 0.001)
    ssq = vol * math.sqrt(tau)
    if ssq < 1e-8:
        return 0.99 if spot >= spot_open else 0.01
    d2 = math.log(spot / spot_open) / ssq - ssq / 2.0
    return max(0.01, min(0.99, _ncdf(d2)))


def _imbalance(book) -> float:
    b, a = book.total_bid_size, book.total_ask_size
    t = b + a
    return (b - a) / t if t > 1 else 0.0


class AggressiveEdge(BaseStrategy):
    def __init__(
        self,
        arb_min_edge: float = 0.010,
        dir_entry_max_frac: float = 0.80,
        dir_entry_min_frac: float = 0.01,
        min_model_edge: float = 0.04,
        momentum_lookback: int = 20,
        momentum_threshold: float = 0.0002,
        stale_threshold_s: float = 20.0,
        cash_deploy_frac: float = 0.90,
    ):
        self.arb_min_edge = arb_min_edge
        self.dir_entry_max_frac = dir_entry_max_frac
        self.dir_entry_min_frac = dir_entry_min_frac
        self.min_model_edge = min_model_edge
        self.momentum_lookback = momentum_lookback
        self.momentum_threshold = momentum_threshold
        self.stale_threshold_s = stale_threshold_s
        self.cash_deploy_frac = cash_deploy_frac

        self._arb_entries: dict[str, int] = {}
        self._dir_entered: set[str] = set()
        self._last_cl: dict[str, tuple[float, int]] = {}
        self._fallback_open: dict[str, float] = {}
        self._hist: dict[str, deque] = {
            "BTC": deque(maxlen=300),
            "ETH": deque(maxlen=300),
            "SOL": deque(maxlen=300),
        }
        self._forecasts: dict[str, float] = {}

    def _cl(self, state: MarketState, asset: str) -> float:
        if asset == "BTC":
            return state.chainlink_btc
        if asset == "ETH":
            return state.chainlink_eth
        return state.chainlink_sol

    def _staleness(self, state: MarketState, asset: str) -> float:
        cl = self._cl(state, asset)
        prev = self._last_cl.get(asset)
        if prev is None:
            self._last_cl[asset] = (cl, state.timestamp)
            return 0.0
        p, pt = prev
        if abs(cl - p) > 1e-6:
            self._last_cl[asset] = (cl, state.timestamp)
            return 0.0
        return float(state.timestamp - pt)

    def _momentum(self, asset: str) -> float:
        h = self._hist[asset]
        lb = self.momentum_lookback
        if len(h) < lb:
            return 0.0
        r = list(h)
        base = r[-lb]
        return (r[-1] - base) / base if base > 0 else 0.0

    def _available_cash(self, state: MarketState) -> float:
        return state.cash * self.cash_deploy_frac

    def _shares_remaining(self, slug: str, token: Token, state: MarketState) -> float:
        pos = state.positions.get(slug)
        if pos is None:
            return 500.0
        current = pos.yes_shares if token == Token.YES else pos.no_shares
        return max(0.0, 500.0 - current)

    def _oracle_open(
        self,
        slug: str,
        market: MarketView,
        cl_now: float,
        state: MarketState,
    ) -> float:
        if market.chainlink_open > 0:
            return market.chainlink_open
        if slug in self._fallback_open:
            return self._fallback_open[slug]
        if cl_now > 0 and state.timestamp >= market.start_ts:
            self._fallback_open[slug] = cl_now
            return cl_now
        return 0.0

    def on_tick(self, state: MarketState) -> list[Order]:
        # Binance BTC for momentum; ETH/SOL use Chainlink spot (no Binance in state)
        if state.btc_mid > 0:
            self._hist["BTC"].append(state.btc_mid)
        for asset in ("ETH", "SOL"):
            cl = self._cl(state, asset)
            if cl > 0:
                self._hist[asset].append(cl)

        orders: list[Order] = []
        self._forecasts = {}
        avail_cash = self._available_cash(state)

        for slug, market in state.markets.items():
            asset = _asset_from_slug(slug)
            intv = _interval_from_slug(slug)
            cl_now = self._cl(state, asset)

            cl_open = self._oracle_open(slug, market, cl_now, state)

            if cl_open > 0 and cl_now > 0:
                vol = _VOL.get((asset, intv), 0.006)
                fair = _fair_prob(cl_now, cl_open, vol, market.time_remaining_frac)
                self._forecasts[slug] = fair
            else:
                self._forecasts[slug] = 0.5
                fair = 0.5

            yes_ask = market.yes_ask
            no_ask = market.no_ask
            if yes_ask <= 0 or no_ask <= 0:
                continue

            combined = yes_ask + no_ask
            arb_edge = 1.0 - combined
            arb_count = self._arb_entries.get(slug, 0)
            if arb_edge >= self.arb_min_edge and arb_count < 5:
                max_arb = _MAX_ENTRY.get(intv, 300)
                size_by_edge = min(max_arb, arb_edge * 5000)
                size_by_cap = min(
                    self._shares_remaining(slug, Token.YES, state),
                    self._shares_remaining(slug, Token.NO, state),
                )
                size_by_cash = avail_cash / combined if combined > 0 else 0
                arb_size = max(10.0, min(size_by_edge, size_by_cap, size_by_cash, max_arb))
                cost = arb_size * combined
                if cost <= avail_cash and arb_size >= 10:
                    orders.append(Order(slug, Token.YES, Side.BUY, arb_size, yes_ask))
                    orders.append(Order(slug, Token.NO, Side.BUY, arb_size, no_ask))
                    self._arb_entries[slug] = arb_count + 1
                    avail_cash -= cost
                    continue

            if market.time_remaining_frac < self.dir_entry_min_frac:
                continue
            if market.time_remaining_frac > self.dir_entry_max_frac:
                continue
            if cl_open <= 0 or cl_now <= 0:
                continue

            stale = self._staleness(state, asset)
            if stale > self.stale_threshold_s:
                continue

            mom = self._momentum(asset)
            yes_winning = cl_now > cl_open
            no_winning = cl_now < cl_open

            if yes_winning:
                token = Token.YES
                ask = yes_ask
                edge_d = fair - ask
                if mom < -self.momentum_threshold:
                    continue
                if _imbalance(market.yes_book) < -0.35:
                    continue
                if market.yes_book.total_ask_size < _MIN_BOOK_DEPTH:
                    continue
            elif no_winning:
                token = Token.NO
                ask = no_ask
                edge_d = (1.0 - fair) - ask
                if mom > self.momentum_threshold:
                    continue
                if _imbalance(market.yes_book) > 0.35:
                    continue
                if market.no_book.total_ask_size < _MIN_BOOK_DEPTH:
                    continue
            else:
                continue

            if edge_d < self.min_model_edge:
                continue

            if slug in self._dir_entered:
                if edge_d < self.min_model_edge * 2.0:
                    continue

            if ask > 0.85:
                continue

            max_size = _MAX_ENTRY.get(intv, 300)
            edge_fraction = min(1.0, edge_d / 0.15)
            size_by_edge = max(20.0, max_size * edge_fraction)
            size_by_cap = self._shares_remaining(slug, token, state)
            size_by_cash = avail_cash / ask if ask > 0 else 0
            size = min(size_by_edge, size_by_cap, size_by_cash, max_size)
            if size < 15:
                continue
            cost = size * ask
            if cost > avail_cash:
                continue
            orders.append(
                Order(
                    market_slug=slug,
                    token=token,
                    side=Side.BUY,
                    size=size,
                    limit_price=min(ask + 0.015, 0.97),
                )
            )
            self._dir_entered.add(slug)
            avail_cash -= cost

        return orders

    def on_fill(self, fill: Fill) -> None:
        pass

    def on_settlement(self, settlement: Settlement) -> None:
        slug = settlement.market_slug
        self._arb_entries.pop(slug, None)
        self._dir_entered.discard(slug)
        self._fallback_open.pop(slug, None)
        self._forecasts.pop(slug, None)

    def get_forecasts(self, state: MarketState) -> dict[str, float]:
        return dict(self._forecasts)
