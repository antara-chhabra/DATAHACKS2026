"""
ClaudeHybridWinner — Maximum P&L Strategy for DATAHACKS 2026
=============================================================

Three-layer edge stack executed every tick:

  Layer 0  Profit-taking sells  — lock in near-certain wins (bid ≥ 0.92),
                                   freeing cash to compound into new trades.
  Layer 1  Complete-set arb     — buy YES + NO when combined ask < 1 − edge.
                                   Guaranteed $1 at settlement; pure risk-free alpha.
  Layer 2  Directional trades   — three signals combined into a confidence score:
                                     a) Black-Scholes fair value  (BTC markets only)
                                     b) Order-book imbalance      (all markets)
                                     c) BTC momentum              (all markets, corr-weighted)

Allowed imports: stdlib + numpy + pandas + scipy.
Constraints: $10k start, max 500 shares per token per market, no shorting,
             T→T+1 execution latency, book staleness < 5 s.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Optional

import numpy as np

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


# ── Tunable parameters ───────────────────────────────────────────────────────

# Layer 1 – Arbitrage
ARB_MIN_EDGE    = 0.012   # min (1 − yes_ask − no_ask) to enter; 1.2% floor
ARB_MAX_ENTRIES = 20      # max arb re-entries per market (position cap enforced separately)
ARB_BASE_SIZE   = 100.0   # base shares per arb leg; scales up with edge quality

# Layer 2 – Directional
DIR_MIN_CONF    = 0.28    # minimum |combined signal| to trade
DIR_BASE_SIZE   = 60.0    # base shares per directional entry
DIR_MIN_LIQ     = 60.0    # minimum ask-side depth on chosen token

# Profit-taking
SELL_BID_THRESH = 0.92    # sell all shares when bid ≥ this (lock near-certain win)

# BTC momentum
BTC_HIST_LEN    = 90      # rolling BTC mid-price history (one entry per tick/second)
BTC_NORM_MOVE   = 0.0010  # ±0.1% move maps to ±1.0 signal; tighter = more trades

# Per-interval implied vol for Black-Scholes (empirically calibrated)
_VOL = {"5m": 0.0045, "15m": 0.0080, "hourly": 0.0160}


class ClaudeHybridWinner(BaseStrategy):
    """
    Maximises total P&L across all Polymarket crypto prediction markets.

    No filtering by asset or interval — the strategy runs on everything and
    lets signal quality + position limits self-regulate exposure.
    """

    def __init__(self) -> None:
        # Rolling BTC mid-price history: (unix_ts, mid_price)
        self.btc_hist: deque[tuple[int, float]] = deque(maxlen=BTC_HIST_LEN)

        # Chainlink oracle BTC price recorded at the first tick of each market.
        # Used as the 'strike' for Black-Scholes (markets resolve vs. opening price).
        self.cl_open: dict[str, float] = {}

        # Count of arb entries per market (independent cap per market).
        self.arb_count: dict[str, int] = {}

    # ── Main entry point ─────────────────────────────────────────────────────

    def on_tick(self, state: MarketState) -> list[Order]:
        """Called every second. Returns a flat list of orders to submit."""
        orders: list[Order] = []

        # Keep BTC history fresh
        if state.btc_mid > 0:
            self.btc_hist.append((state.timestamp, state.btc_mid))

        # Pre-compute BTC momentum once per tick; shared across all markets
        btc_mom: float = self._btc_momentum()

        # Track cash committed this tick to prevent over-allocation across markets
        available_cash: float = state.cash

        for slug, market in state.markets.items():

            # Record Chainlink open on first observation (strike for BS model)
            if slug not in self.cl_open and state.chainlink_btc > 0:
                self.cl_open[slug] = state.chainlink_btc

            # Never touch markets with < 5 s remaining — latency risk
            if market.time_remaining_s < 5:
                continue

            # ── Layer 0: profit-taking sells ─────────────────────────────
            orders += self._sell_pass(slug, market, state)

            # ── Layer 1: complete-set arbitrage ──────────────────────────
            arb = self._arb_pass(slug, market, state, available_cash)
            orders += arb
            if arb:
                # Deduct committed cash so later markets in the same tick
                # don't over-draw the same balance.
                for o in arb:
                    ask = market.yes_ask if o.token == Token.YES else market.no_ask
                    available_cash -= o.size * ask
                # Arb already deploys capital here; skip directional this tick.
                continue

            # ── Layers 2 & 3: directional trade ──────────────────────────
            dir_orders = self._directional_pass(slug, market, state, btc_mom, available_cash)
            orders += dir_orders
            for o in dir_orders:
                ask = market.yes_ask if o.token == Token.YES else market.no_ask
                available_cash -= o.size * ask

        return orders

    # ── Signal: BTC momentum ─────────────────────────────────────────────────

    def _btc_momentum(self) -> float:
        """
        Dual-window BTC momentum signal normalised to [−1, +1].
        +1 → strong uptrend (favours YES on 'above' markets).

        Blends a 30-tick short window (60%) with a 60-tick long window (40%)
        to reduce noise while still catching rapid moves.
        """
        n = len(self.btc_hist)
        if n < 10:
            return 0.0

        prices = np.array([p for _, p in self.btc_hist], dtype=np.float64)
        now = prices[-1]

        p30 = prices[max(0, n - 30)]
        p60 = prices[max(0, n - 60)]

        ret30 = (now / p30 - 1.0) if p30 > 0 else 0.0
        ret60 = (now / p60 - 1.0) if p60 > 0 else 0.0

        raw = 0.6 * ret30 + 0.4 * ret60
        return float(np.clip(raw / BTC_NORM_MOVE, -1.0, 1.0))

    # ── Signal: order-book imbalance ─────────────────────────────────────────

    @staticmethod
    def _imbalance(book) -> float:
        """
        (total_bid_depth − total_ask_depth) / (total_bid_depth + total_ask_depth).
        Result ∈ [−1, +1]. Positive = more buying pressure (bids dominate).
        """
        b = book.total_bid_size
        a = book.total_ask_size
        total = b + a
        return 0.0 if total < 1e-9 else (b - a) / total

    # ── Signal: Black-Scholes fair P(YES) ────────────────────────────────────

    def _model_p_yes(self, slug: str, market: MarketView, spot: float) -> float:
        """
        Geometric Brownian Motion estimate of P(YES) for BTC markets.

        Markets resolve YES if the Chainlink close > Chainlink open, so the
        opening oracle price is the natural 'strike'. For 'below' markets,
        YES = BTC < open, so we return 1 − P(above).

        Returns 0.5 (neutral) for non-BTC markets or missing data.
        """
        if not (slug.startswith("btc-") or slug.startswith("bitcoin-")):
            return 0.5

        strike = self.cl_open.get(slug, 0.0)
        if strike <= 0 or spot <= 0:
            return 0.5

        # Determine interval label for vol lookup
        if "5m" in slug:
            vol = _VOL["5m"]
        elif "15m" in slug:
            vol = _VOL["15m"]
        else:
            vol = _VOL["hourly"]

        tau = max(market.time_remaining_frac, 0.001)
        sigma_sqrt_tau = vol * math.sqrt(tau)

        if sigma_sqrt_tau < 1e-9:
            return 0.99 if spot >= strike else 0.01

        # Black-Scholes d2 (no drift for risk-neutral prediction)
        d2 = math.log(spot / strike) / sigma_sqrt_tau - sigma_sqrt_tau / 2.0
        p_above = max(0.01, min(0.99, 0.5 * (1.0 + math.erf(d2 / math.sqrt(2.0)))))

        return p_above if "above" in slug else (1.0 - p_above)

    # ── Layer 0: Profit-taking sells ─────────────────────────────────────────

    def _sell_pass(
        self, slug: str, market: MarketView, state: MarketState
    ) -> list[Order]:
        """
        Sell entire position when the best bid reaches SELL_BID_THRESH.

        Rationale: at bid ≥ 0.92 the market is pricing the outcome at 92%+
        certainty. Locking in $0.92 now frees cash to compound into new arbs
        or directional trades before this position settles.
        """
        orders: list[Order] = []
        pos = state.positions.get(slug)
        if not pos:
            return orders

        if pos.yes_shares > 0 and market.yes_bid >= SELL_BID_THRESH:
            orders.append(Order(
                market_slug=slug,
                token=Token.YES,
                side=Side.SELL,
                size=pos.yes_shares,
                limit_price=market.yes_bid,
            ))

        if pos.no_shares > 0 and market.no_bid >= SELL_BID_THRESH:
            orders.append(Order(
                market_slug=slug,
                token=Token.NO,
                side=Side.SELL,
                size=pos.no_shares,
                limit_price=market.no_bid,
            ))

        return orders

    # ── Layer 1: Complete-set arbitrage ──────────────────────────────────────

    def _arb_pass(
        self, slug: str, market: MarketView, state: MarketState, available_cash: float
    ) -> list[Order]:
        """
        Buy YES + NO together when their combined ask is below $1 by at least
        ARB_MIN_EDGE. At settlement, exactly one side pays $1, so the combined
        position is worth $1 regardless of outcome.

        Edge = 1 − (yes_ask + no_ask).  E.g. yes_ask=0.47, no_ask=0.50 → edge=0.03.

        Size is scaled aggressively with edge quality (up to 4× base at 5× min edge),
        then capped by: position headroom, book liquidity, and available cash.
        """
        ya, na = market.yes_ask, market.no_ask
        if ya <= 0 or na <= 0:
            return []

        combined = ya + na
        edge = 1.0 - combined
        if edge < ARB_MIN_EDGE:
            return []

        if self.arb_count.get(slug, 0) >= ARB_MAX_ENTRIES:
            return []

        # Position headroom (can hold max 500 of each token)
        pos = state.positions.get(slug)
        yes_held = pos.yes_shares if pos else 0.0
        no_held  = pos.no_shares  if pos else 0.0
        headroom = min(500.0 - yes_held, 500.0 - no_held)
        if headroom <= 1:
            return []

        # Scale: larger edge → deploy more capital
        edge_mult = min(edge / ARB_MIN_EDGE, 4.0)   # ×1 at min edge, ×4 at 5× min
        book_liq  = min(
            market.yes_book.total_ask_size,
            market.no_book.total_ask_size,
        )
        size = min(
            ARB_BASE_SIZE * edge_mult,        # edge-scaled target
            headroom,                          # position cap
            book_liq * 0.80,                  # don't sweep > 80% of available depth
            available_cash * 0.90 / combined,  # cash cap (keep 10% buffer)
        )

        if size < 5:
            return []

        self.arb_count[slug] = self.arb_count.get(slug, 0) + 1
        return [
            Order(market_slug=slug, token=Token.YES, side=Side.BUY,
                  size=size, limit_price=ya),
            Order(market_slug=slug, token=Token.NO,  side=Side.BUY,
                  size=size, limit_price=na),
        ]

    # ── Layers 2 & 3: Directional trading ────────────────────────────────────

    def _directional_pass(
        self,
        slug: str,
        market: MarketView,
        state: MarketState,
        btc_mom: float,
        available_cash: float,
    ) -> list[Order]:
        """
        Combine three signals into a single YES-directional confidence score.

        Signal 1 — Fair value (BTC markets, weight 0.50 when available, else 0):
            Signed edge = (model_P_yes − market_mid_yes) / 0.10.
            Positive → market is underpricing YES → buy YES.

        Signal 2 — Book imbalance (all markets, weight 0.25 / 0.55):
            (YES_bid_depth − YES_ask_depth) − (NO_bid_depth − NO_ask_depth), normalised.
            Positive → more YES buying pressure in the book.

        Signal 3 — BTC momentum (all markets, weight 0.25 / 0.45):
            Adjusted for crypto correlation (1.0 for BTC, 0.35 for ETH/SOL) and
            flipped for 'below' markets (rising BTC hurts YES in a 'below' contract).

        combined > 0 → buy YES.   combined < 0 → buy NO.
        |combined| < DIR_MIN_CONF → no trade.
        """

        # ── Signal 1: BS fair value ───────────────────────────────────────
        p_yes_model = self._model_p_yes(slug, market, state.chainlink_btc)
        if market.yes_bid > 0 and market.yes_ask > 0:
            mkt_mid = (market.yes_bid + market.yes_ask) / 2.0
        elif market.yes_price > 0:
            mkt_mid = market.yes_price
        else:
            mkt_mid = 0.50
        # ±1 at ±10 cent model/market divergence; clipped to [−1.5, 1.5]
        fv_signal = float(np.clip((p_yes_model - mkt_mid) / 0.10, -1.5, 1.5))

        # ── Signal 2: Book imbalance ──────────────────────────────────────
        # Positive = YES book bids dominate; negative = NO book bids dominate
        yes_imb = self._imbalance(market.yes_book)
        no_imb  = self._imbalance(market.no_book)
        book_signal = float(np.clip((yes_imb - no_imb) / 2.0, -1.0, 1.0))

        # ── Signal 3: BTC momentum ────────────────────────────────────────
        is_btc = slug.startswith("btc-") or slug.startswith("bitcoin-")
        is_eth = slug.startswith("eth-") or slug.startswith("ethereum-")
        is_sol = slug.startswith("sol-") or slug.startswith("solana-")

        # BTC fully correlated; ETH/SOL partially follow BTC moves
        corr = 1.0 if is_btc else (0.40 if (is_eth or is_sol) else 0.20)

        # 'above' markets: rising BTC → YES more likely (+1 direction)
        # 'below' markets: rising BTC → NO more likely (−1 direction)
        direction = 1.0 if "above" in slug else -1.0
        mom_signal = float(np.clip(btc_mom * corr * direction, -1.0, 1.0))

        # ── Combine signals ───────────────────────────────────────────────
        has_btc_model = is_btc and self.cl_open.get(slug, 0.0) > 0
        if has_btc_model:
            # Fair value is reliable; give it the majority of the weight
            combined = 0.50 * fv_signal + 0.25 * book_signal + 0.25 * mom_signal
        else:
            # No fundamental anchor for ETH/SOL — rely on microstructure + momentum
            combined = 0.55 * book_signal + 0.45 * mom_signal

        abs_c = abs(combined)
        if abs_c < DIR_MIN_CONF:
            return []

        # ── Determine which token to buy ──────────────────────────────────
        token = Token.YES if combined > 0 else Token.NO
        ask   = market.yes_ask if token == Token.YES else market.no_ask
        liq   = (market.yes_book.total_ask_size
                 if token == Token.YES
                 else market.no_book.total_ask_size)

        # Sanity checks: valid ask, not trading near-certain-loss tokens,
        # and enough depth to fill a reasonable order
        if ask <= 0 or ask > 0.96 or liq < DIR_MIN_LIQ:
            return []

        # ── Position sizing ───────────────────────────────────────────────
        # time_factor: scale down when very little time remains (edge decays
        # near expiry for wrong positions); scale up early when more alpha left
        time_factor = min(1.0, market.time_remaining_frac * 1.5)
        size = DIR_BASE_SIZE * abs_c * time_factor

        # Hard caps: position limit, available cash, book depth
        pos  = state.positions.get(slug)
        held = ((pos.yes_shares if token == Token.YES else pos.no_shares)
                if pos else 0.0)
        size = min(
            size,
            500.0 - held,                  # position limit
            available_cash * 0.90 / ask,   # cash limit (10% buffer)
            liq * 0.50,                    # don't take > 50% of visible depth
        )

        if size < 5:
            return []

        return [Order(
            market_slug=slug,
            token=token,
            side=Side.BUY,
            size=round(size, 1),
            limit_price=ask,
        )]

    # ── Optional callbacks ────────────────────────────────────────────────────

    def on_fill(self, fill: Fill) -> None:
        """No per-fill bookkeeping needed; position limits are read from state."""
        pass

    def on_settlement(self, settlement: Settlement) -> None:
        """Discard per-market state for settled markets to prevent memory growth."""
        slug = settlement.market_slug
        self.cl_open.pop(slug, None)
        self.arb_count.pop(slug, None)
