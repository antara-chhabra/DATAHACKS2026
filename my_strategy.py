"""
PrismFV — Fair-value + arbitrage strategy for BTC/ETH/SOL prediction markets.

Design overview
---------------
Three signal sources feed one order pipeline:

  1. Complete-set arbitrage (all assets).
     Buy YES+NO when ask_sum < 1 - eps. Guaranteed $1 payout at settlement.

  2. Black-Scholes fair value (BTC only — it's the one asset with a runtime price).
     Compute P(YES) = N(d2) using chainlink_btc vs. the price at market open,
     with a learned realized-volatility estimator that updates every tick.
     Trade when |fair - market| > edge_threshold.

  3. BTC-correlation cross-asset signal (ETH/SOL).
     We don't get an ETH/SOL price at runtime, but crypto majors are ~0.7+
     correlated intraday. When BTC has moved strongly since an ETH/SOL
     market opened, the same-direction bet on that market is weakly positive
     EV. We use a smaller size + higher edge threshold for these.

Risk controls
-------------
  * Per-market cash cap (PER_MARKET_MAX_COST) — one bad market can't wipe us.
  * Conservative position limit (MAX_POSITION_SHARES < 500) — avoid partial
    fills at the hard cap.
  * Edge-scaled position sizing.
  * Complete-set arb legs are held to settlement — we never sell one side of a
    hedged YES+NO position (that would destroy locked-in arb P&L).
  * Exits: BTC directional only — take profit when model edge vs mid collapses.
  * ETH/SOL directional is opt-in (default off) — no on-chain ETH/SOL in state,
    so proxy trades are mostly spread cost.
  * Don't re-enter the same side twice — prevents compounding into a losing
    conviction.

P&L focus (maximize within engine rules)
----------------------------------------
  * Deploy up to position/cash limits: scaled arb, interval-scaled BTC edge,
    optional book confirmation, profit-taking on one-sided winners.
  * Never break a balanced complete-set hedge with single-leg sells.

Asset identification (from slug prefix):
  BTC: "btc-" / "bitcoin-"
  ETH: "eth-" / "ethereum-"
  SOL: "sol-" / "solana-"
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
    PositionView,
    Settlement,
    Side,
    Token,
)


# ── Config ───────────────────────────────────────────────────────────────────

# ETH/SOL have no runtime oracle in MarketState — proxy directional trades
# tend to pay spread without edge. Off by default for P&L; still allow arb.
ENABLE_ETH_SOL_DIRECTIONAL = False

# BS / fair-value directional on BTC markets. When False, strategy is
# complete-set arb only (often best P&L per trade after costs).
ENABLE_BTC_DIRECTIONAL = True

# BTC directional intervals — stricter edge on longer windows.
BTC_DIRECTIONAL_INTERVALS = frozenset({"5m", "15m", "hourly"})
# Min time-remaining fraction to *start* a new directional (early window).
BTC_ENTRY_MIN_REMAINING_FRAC = {"5m": 0.72, "15m": 0.82, "hourly": 0.88}
# Edge threshold scales with horizon (wider threshold = fewer false trades).
FV_BTC_EDGE_BY_INTERVAL = {"5m": 0.058, "15m": 0.074, "hourly": 0.088}
FV_BTC_BASE_BY_INTERVAL = {"5m": 26.0, "15m": 22.0, "hourly": 18.0}
FV_BTC_MAX_BY_INTERVAL = {"5m": 95.0, "15m": 80.0, "hourly": 65.0}

# Early sells vs settlement — off by default; profit-take handles locking gains.
ENABLE_DIRECTIONAL_EXITS = False

# Lock near-certain wins on *one-sided* inventory (frees cash for more arb/edge).
PROFIT_TAKE_BID = 0.91

# Arbitrage (primary risk-free alpha) — size up to headroom & book depth.
ARB_MIN_EDGE = 0.008
ARB_SIZE = 72.0
ARB_MAX_ENTRIES_PER_MKT = 14
ARB_ENTRY_COOLDOWN_S = 4

# Fair value — BTC (defaults overridden per interval above)
FV_BTC_EDGE = 0.058
FV_BTC_BASE_SIZE = 26.0
FV_BTC_MAX_SIZE = 95.0

# Optional: require microstructure to agree (reduces fighting the tape).
REQUIRE_BOOK_ALIGN = True
BOOK_ALIGN_THRESH = 0.06

# Fair value — ETH/SOL via BTC correlation (only if ENABLE_ETH_SOL_DIRECTIONAL)
FV_CORR_EDGE = 0.12
FV_CORR_BASE_SIZE = 18.0
FV_CORR_MAX_SIZE = 40.0
BTC_CORR_WEIGHT = 0.45

# Vol estimation
VOL_WINDOW_SECONDS = 15 * 60  # 15 min rolling window of BTC log-returns
VOL_MIN_SAMPLES = 30          # need this many samples before trusting model
VOL_FALLBACK_15M = 0.005      # ~0.5% typical BTC 15-min stdev — used until warmed up

# Risk / sizing — push toward 500-share cap / meaningful notional per market.
PER_MARKET_MAX_COST = 420.0
MAX_POSITION_SHARES = 495.0
MIN_CASH_RESERVE = 120.0
MIN_TIME_REMAINING_S = 35.0
MIN_YES_ASK = 0.03
MAX_YES_ASK = 0.97

# Exits (directional only — never applied to hedged YES+NO arb inventory)
EXIT_EDGE = 0.012

# Misc
ASSET_BTC = "BTC"
ASSET_ETH = "ETH"
ASSET_SOL = "SOL"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _asset_from_slug(slug: str) -> str | None:
    """Identify underlying asset from market slug prefix."""
    s = slug.lower()
    if s.startswith("btc-") or s.startswith("bitcoin-"):
        return ASSET_BTC
    if s.startswith("eth-") or s.startswith("ethereum-"):
        return ASSET_ETH
    if s.startswith("sol-") or s.startswith("solana-"):
        return ASSET_SOL
    return None


def _standard_normal_cdf(x: float) -> float:
    """Phi(x) via erf — stdlib-only so we don't need scipy at runtime."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_prob_up(
    price_now: float,
    price_open: float,
    sigma: float,           # stdev of log-return over the full market window
    time_remaining_frac: float,
) -> float:
    """
    Black-Scholes P(price at expiry >= price_open).

    Model: ln(S_T / S_now) ~ N(-sigma^2*tau/2, sigma^2*tau). We want
    P(S_T >= S_open) = P(ln(S_T/S_now) >= ln(S_open/S_now)).

    d2 = (ln(S_now/S_open) - sigma^2*tau/2) / (sigma*sqrt(tau))
    P(YES) = Phi(d2)

    tau is fraction of the market window remaining.
    """
    if price_open <= 0 or price_now <= 0:
        return 0.5

    tau = max(time_remaining_frac, 1e-4)
    s = sigma if sigma > 0 else 1e-4
    s_sqrt_tau = s * math.sqrt(tau)

    if s_sqrt_tau < 1e-6:
        # essentially zero time/vol left — outcome is already determined
        return 0.999 if price_now >= price_open else 0.001

    log_moneyness = math.log(price_now / price_open)
    d2 = (log_moneyness - s_sqrt_tau * s_sqrt_tau * 0.5) / s_sqrt_tau
    p = _standard_normal_cdf(d2)

    # clip away from 0/1 so limit_price validators (0 < p < 1) stay happy
    return max(0.005, min(0.995, p))


def _clip_limit_price(p: float) -> float:
    """Engine rejects limit prices that are <=0 or >=1. Squeeze into (0.01, 0.99)."""
    return max(0.01, min(0.99, p))


def _book_pressure_yes(mkt: MarketView) -> float:
    """
    Normalized YES-book pressure minus NO-book pressure in [-1, 1].
    Positive → more bid depth on YES vs asks; used as a confirm for YES buys.
    """
    yb = mkt.yes_book.total_bid_size
    ya = mkt.yes_book.total_ask_size
    nb = mkt.no_book.total_bid_size
    na = mkt.no_book.total_ask_size
    y = (yb - ya) / (yb + ya) if (yb + ya) > 1e-6 else 0.0
    n = (nb - na) / (nb + na) if (nb + na) > 1e-6 else 0.0
    return max(-1.0, min(1.0, (y - n) / 2.0))


def _is_hedged_complete_set(pos: PositionView | None) -> bool:
    """
    True when we hold both YES and NO at meaningful size (complete-set arb).

    Selling one leg for 'fair value' would destroy the locked $1 payout profile;
    directional adds on top would un-hedge the book.
    """
    if not pos:
        return False
    y, n = pos.yes_shares, pos.no_shares
    if y < 3.0 or n < 3.0:
        return False
    return abs(y - n) / max(y, n) <= 0.28


# ── Rolling volatility estimator for BTC ──────────────────────────────────────


class RollingVol:
    """
    Keeps a deque of recent BTC log-returns and computes stdev over the
    15-minute window. This scales naturally — a 15-min realized stdev is
    exactly the sigma we want for the 15-min market fair-value formula,
    and for 5m markets we rescale by sqrt(1/3).
    """

    def __init__(self, window_s: int = VOL_WINDOW_SECONDS):
        self.window_s = window_s
        # (ts_sec, log_return) pairs
        self._returns: deque[tuple[int, float]] = deque()
        self._last_price: float = 0.0
        self._last_ts: int = 0

    def update(self, ts: int, price: float) -> None:
        if price <= 0:
            return
        if self._last_price > 0 and ts > self._last_ts:
            try:
                r = math.log(price / self._last_price)
                self._returns.append((ts, r))
            except (ValueError, ZeroDivisionError):
                pass
        self._last_price = price
        self._last_ts = ts

        # Evict anything older than window_s
        cutoff = ts - self.window_s
        while self._returns and self._returns[0][0] < cutoff:
            self._returns.popleft()

    def sigma_per_interval(self, interval_seconds: int) -> float:
        """
        Return an estimate of stdev of BTC log-returns over `interval_seconds`.

        We estimate per-second vol from the buffer, then scale by
        sqrt(interval_seconds) (Brownian motion scaling). This means we
        DON'T need a separate estimator per market interval.
        """
        n = len(self._returns)
        if n < VOL_MIN_SAMPLES:
            # scale fallback (which is a 15-min stdev) to requested interval
            return VOL_FALLBACK_15M * math.sqrt(interval_seconds / 900.0)

        # per-second stdev (returns are 1-sec log returns)
        mean = sum(r for _, r in self._returns) / n
        var = sum((r - mean) ** 2 for _, r in self._returns) / max(n - 1, 1)
        per_sec_stdev = math.sqrt(max(var, 0.0))
        return per_sec_stdev * math.sqrt(interval_seconds)


# ── Strategy ─────────────────────────────────────────────────────────────────


class MyStrategy(BaseStrategy):
    """
    PrismFV: fair-value + arbitrage for BTC/ETH/SOL binary markets.
    """

    def __init__(self) -> None:
        # Rolling realized vol from state.btc_mid
        self._vol = RollingVol()

        # Record the underlying (BTC oracle) price at each market's open.
        # Keyed by slug. First tick we see a market, we pin this.
        self._btc_at_market_open: dict[str, float] = {}

        # For ETH/SOL we have no runtime underlying — but we CAN pin BTC at
        # their open, and use BTC's move since then as a weak directional proxy.
        self._btc_at_market_open_eth_sol: dict[str, float] = {}

        # Arb bookkeeping — number of times we've arbed each market
        self._arb_entries: dict[str, int] = {}

        # Track cost basis per market (to enforce PER_MARKET_MAX_COST)
        self._cost_by_market: dict[str, float] = {}

        # Track which side we've directionally bought in each market
        # so we don't compound into a losing conviction.
        # slug -> "YES" or "NO" (the directional side we've entered)
        self._directional_side: dict[str, str] = {}

        # Last interval -> interval seconds map (cache)
        self._interval_seconds = {"5m": 300, "15m": 900, "hourly": 3600}

        # Cooldown trackers — prevent spamming the same order every tick.
        # Key: slug -> tick we last placed that action type.
        self._last_entry_tick: dict[str, int] = {}
        self._last_exit_tick: dict[str, int] = {}

        # Re-entry cooldown in seconds. Because fills happen at T+1 we need
        # at least 1 second, but a few seconds is more robust to market noise.
        self._entry_cooldown_s = 9
        self._exit_cooldown_s = 5
        self._last_arb_tick: dict[str, int] = {}

    # ── Main tick handler ────────────────────────────────────────────────────

    def on_tick(self, state: MarketState) -> list[Order]:
        orders: list[Order] = []

        # 1. Update volatility model from Binance BTC mid
        if state.btc_mid > 0:
            self._vol.update(state.timestamp, state.btc_mid)

        # 2. Pin the underlying at each market's open
        for slug, mkt in state.markets.items():
            if slug not in self._btc_at_market_open and state.chainlink_btc > 0:
                self._btc_at_market_open[slug] = state.chainlink_btc

        # 3. For each market, decide actions (track cash so one tick doesn't
        # over-commit vs. validation in the execution engine).
        available_cash = state.cash
        for slug, mkt in state.markets.items():
            # Safety: skip markets with no book at all
            if mkt.yes_ask <= 0 and mkt.no_ask <= 0:
                continue

            # ── Profit-taking (one-sided winners only; never split a hedged arb) ─
            pt_orders = self._try_profit_take(slug, mkt, state)
            if pt_orders:
                orders.extend(pt_orders)
                for o in pt_orders:
                    if o.side == Side.SELL:
                        if o.token == Token.YES and mkt.yes_bid > 0:
                            available_cash += o.size * mkt.yes_bid
                        elif o.token == Token.NO and mkt.no_bid > 0:
                            available_cash += o.size * mkt.no_bid

            # ── Arbitrage check (any asset) ──────────────────────────────
            arb_orders = self._try_arb(slug, mkt, state, available_cash, state.timestamp)
            if arb_orders:
                # Each arb is size * (yes_ask + no_ask)
                cost = sum(o.size * (o.limit_price or 0) for o in arb_orders)
                available_cash -= cost
                orders.extend(arb_orders)
                continue  # arb takes priority; don't layer a directional on top

            # ── Directional (all 3 assets via different paths) ───────────
            dir_orders = self._try_directional(slug, mkt, state, available_cash)
            if dir_orders:
                cost = sum(o.size * (o.limit_price or 0) for o in dir_orders
                           if o.side == Side.BUY)
                available_cash -= cost
                orders.extend(dir_orders)

            # ── Exits ─────────────────────────────────────────────────────
            exit_orders = self._try_exits(slug, mkt, state)
            orders.extend(exit_orders)

        return orders

    # ── Profit-taking (one-sided) ─────────────────────────────────────────────

    def _try_profit_take(
        self, slug: str, mkt: MarketView, state: MarketState
    ) -> list[Order]:
        """Sell into very high bids to recycle capital (never split hedged arb)."""
        pos = state.positions.get(slug)
        if not pos:
            return []
        if _is_hedged_complete_set(pos):
            return []
        out: list[Order] = []
        if pos.yes_shares >= 3.0 and mkt.yes_bid >= PROFIT_TAKE_BID:
            out.append(
                Order(
                    market_slug=slug,
                    token=Token.YES,
                    side=Side.SELL,
                    size=pos.yes_shares,
                    limit_price=_clip_limit_price(mkt.yes_bid),
                )
            )
        if pos.no_shares >= 3.0 and mkt.no_bid >= PROFIT_TAKE_BID:
            out.append(
                Order(
                    market_slug=slug,
                    token=Token.NO,
                    side=Side.SELL,
                    size=pos.no_shares,
                    limit_price=_clip_limit_price(mkt.no_bid),
                )
            )
        return out

    # ── Arbitrage ────────────────────────────────────────────────────────────

    def _try_arb(
        self, slug: str, mkt: MarketView, state: MarketState, cash: float, ts: int
    ) -> list[Order]:
        yes_ask = mkt.yes_ask
        no_ask = mkt.no_ask
        if yes_ask <= 0 or no_ask <= 0:
            return []

        combined = yes_ask + no_ask
        edge = 1.0 - combined
        if edge < ARB_MIN_EDGE:
            return []

        # Don't over-trade the same market
        if self._arb_entries.get(slug, 0) >= ARB_MAX_ENTRIES_PER_MKT:
            return []

        last_arb = self._last_arb_tick.get(slug, -10_000)
        if ts - last_arb < ARB_ENTRY_COOLDOWN_S:
            return []

        # Scale size with edge quality (more edge → deploy more)
        edge_mult = min(edge / ARB_MIN_EDGE, 4.0)
        size = ARB_SIZE * edge_mult

        pos = state.positions.get(slug)
        yes_held = pos.yes_shares if pos else 0.0
        no_held = pos.no_shares if pos else 0.0
        headroom = min(500.0 - yes_held, 500.0 - no_held)
        if headroom < 5.0:
            return []

        yes_top = mkt.yes_book.asks[0].size if mkt.yes_book.asks else 0.0
        no_top = mkt.no_book.asks[0].size if mkt.no_book.asks else 0.0
        top_liq = min(yes_top, no_top) * 0.88
        depth_liq = min(
            mkt.yes_book.total_ask_size * 0.80,
            mkt.no_book.total_ask_size * 0.80,
        )
        size = min(size, headroom, top_liq, depth_liq)
        if size < 5:
            return []

        per_market_cost = self._cost_by_market.get(slug, 0.0)
        if per_market_cost + size * combined > PER_MARKET_MAX_COST:
            size = max(0.0, (PER_MARKET_MAX_COST - per_market_cost) / combined)
            if size < 5:
                return []

        total_cost = size * combined
        if cash - total_cost < MIN_CASH_RESERVE:
            return []

        self._arb_entries[slug] = self._arb_entries.get(slug, 0) + 1
        self._last_arb_tick[slug] = ts
        self._last_entry_tick[slug] = ts

        return [
            Order(
                market_slug=slug,
                token=Token.YES,
                side=Side.BUY,
                size=size,
                limit_price=_clip_limit_price(yes_ask),
            ),
            Order(
                market_slug=slug,
                token=Token.NO,
                side=Side.BUY,
                size=size,
                limit_price=_clip_limit_price(no_ask),
            ),
        ]

    # ── Directional fair-value ───────────────────────────────────────────────

    def _try_directional(
        self,
        slug: str,
        mkt: MarketView,
        state: MarketState,
        cash: float,
    ) -> list[Order]:
        asset = _asset_from_slug(slug)
        if asset is None:
            return []

        if asset in (ASSET_ETH, ASSET_SOL) and not ENABLE_ETH_SOL_DIRECTIONAL:
            return []

        if asset == ASSET_BTC and not ENABLE_BTC_DIRECTIONAL:
            return []

        pos_early = state.positions.get(slug)
        if _is_hedged_complete_set(pos_early):
            return []

        if mkt.time_remaining_s < MIN_TIME_REMAINING_S:
            return []

        if mkt.yes_ask <= MIN_YES_ASK or mkt.yes_ask >= MAX_YES_ASK:
            return []

        # Cooldown: don't re-emit directional entries on this market too fast.
        # Fills arrive at T+1, so if we placed an order at T we shouldn't
        # place another at T+1/T+2 — it'll be duplicated, filling (or
        # rejecting) twice.
        last = self._last_entry_tick.get(slug, -10_000)
        if state.timestamp - last < self._entry_cooldown_s:
            return []

        # If we ALREADY have a directional position on this market, don't
        # double down. Exits are handled separately.
        existing_side = self._directional_side.get(slug)
        pos = state.positions.get(slug)
        if pos and (pos.yes_shares > 0 or pos.no_shares > 0) and existing_side:
            return []

        # Compute fair value for this asset
        if asset == ASSET_BTC:
            if mkt.interval not in BTC_DIRECTIONAL_INTERVALS:
                return []
            min_frac = BTC_ENTRY_MIN_REMAINING_FRAC.get(mkt.interval, 0.75)
            if mkt.time_remaining_frac < min_frac:
                return []
            fair = self._btc_fair_value(slug, mkt, state)
            if fair is None:
                return []
            edge_thresh = FV_BTC_EDGE_BY_INTERVAL.get(mkt.interval, FV_BTC_EDGE)
            base_size = FV_BTC_BASE_BY_INTERVAL.get(mkt.interval, FV_BTC_BASE_SIZE)
            max_size = FV_BTC_MAX_BY_INTERVAL.get(mkt.interval, FV_BTC_MAX_SIZE)
        else:
            # ETH/SOL — use BTC correlation proxy
            fair = self._corr_fair_value(slug, mkt, state, asset)
            if fair is None:
                return []
            edge_thresh = FV_CORR_EDGE
            base_size = FV_CORR_BASE_SIZE
            max_size = FV_CORR_MAX_SIZE

        market_mid = mkt.yes_price if mkt.yes_price > 0 else (mkt.yes_bid + mkt.yes_ask) / 2
        if market_mid <= 0:
            return []

        delta = fair - market_mid

        # Scale size by how big the edge is, cap at max_size
        edge_magnitude = abs(delta)
        if edge_magnitude < edge_thresh:
            return []

        if REQUIRE_BOOK_ALIGN and asset == ASSET_BTC:
            bp = _book_pressure_yes(mkt)
            if delta > 0 and bp < BOOK_ALIGN_THRESH:
                return []
            if delta < 0 and bp > -BOOK_ALIGN_THRESH:
                return []

        size_mult = min(edge_magnitude / edge_thresh, 3.5)
        size = min(base_size * size_mult, max_size)

        # Check book depth — don't eat more than 70% of top-of-book
        if delta > 0:
            top_size = mkt.yes_book.asks[0].size if mkt.yes_book.asks else 0.0
            size = min(size, top_size * 0.7)
            if size < 5:
                return []
            # Enforce position cap
            current_pos = state.positions.get(slug)
            current_yes = current_pos.yes_shares if current_pos else 0.0
            if current_yes + size > MAX_POSITION_SHARES:
                size = max(0.0, MAX_POSITION_SHARES - current_yes)
                if size < 5:
                    return []
            if existing_side == "NO":
                return []  # don't flip sides

            # Per-market cost cap
            per_cost = self._cost_by_market.get(slug, 0.0)
            est_cost = size * mkt.yes_ask
            if per_cost + est_cost > PER_MARKET_MAX_COST:
                size = max(0.0, (PER_MARKET_MAX_COST - per_cost) / max(mkt.yes_ask, 0.01))
                if size < 5:
                    return []
                est_cost = size * mkt.yes_ask

            if cash - est_cost < MIN_CASH_RESERVE:
                return []

            self._directional_side[slug] = "YES"
            self._last_entry_tick[slug] = state.timestamp
            # Slightly overshoot the ask to walk 1 level if needed
            limit = _clip_limit_price(min(fair, mkt.yes_ask + 0.01))
            return [Order(
                market_slug=slug,
                token=Token.YES,
                side=Side.BUY,
                size=size,
                limit_price=limit,
            )]

        else:  # delta < 0 — market is rich, buy NO
            top_size = mkt.no_book.asks[0].size if mkt.no_book.asks else 0.0
            size = min(size, top_size * 0.7)
            if size < 5:
                return []

            current_pos = state.positions.get(slug)
            current_no = current_pos.no_shares if current_pos else 0.0
            if current_no + size > MAX_POSITION_SHARES:
                size = max(0.0, MAX_POSITION_SHARES - current_no)
                if size < 5:
                    return []
            if existing_side == "YES":
                return []

            per_cost = self._cost_by_market.get(slug, 0.0)
            est_cost = size * mkt.no_ask
            if per_cost + est_cost > PER_MARKET_MAX_COST:
                size = max(0.0, (PER_MARKET_MAX_COST - per_cost) / max(mkt.no_ask, 0.01))
                if size < 5:
                    return []
                est_cost = size * mkt.no_ask

            if cash - est_cost < MIN_CASH_RESERVE:
                return []

            self._directional_side[slug] = "NO"
            self._last_entry_tick[slug] = state.timestamp
            limit = _clip_limit_price(min(1.0 - fair, mkt.no_ask + 0.01))
            return [Order(
                market_slug=slug,
                token=Token.NO,
                side=Side.BUY,
                size=size,
                limit_price=limit,
            )]

    def _btc_fair_value(
        self, slug: str, mkt: MarketView, state: MarketState
    ) -> float | None:
        """BS fair value for BTC markets using the rolling vol estimator."""
        if state.chainlink_btc <= 0:
            return None
        btc_open = self._btc_at_market_open.get(slug)
        if btc_open is None or btc_open <= 0:
            return None

        interval_s = self._interval_seconds.get(mkt.interval, 300)
        sigma = self._vol.sigma_per_interval(interval_s)

        # Floor sigma — a low-variance trending window can produce
        # pathologically tight BS probabilities (d2 → ∞ even with tiny
        # log-moneyness). Floor at 20% of our fallback so fresh markets
        # don't get degenerate signals.
        interval_floor = VOL_FALLBACK_15M * math.sqrt(interval_s / 900.0) * 0.5
        sigma = max(sigma, interval_floor)

        return _bs_prob_up(
            price_now=state.chainlink_btc,
            price_open=btc_open,
            sigma=sigma,
            time_remaining_frac=mkt.time_remaining_frac,
        )

    def _corr_fair_value(
        self, slug: str, mkt: MarketView, state: MarketState, asset: str
    ) -> float | None:
        """
        Cross-asset fair value for ETH/SOL using BTC as a weak proxy.

        Logic: if BTC moved +X% since the ETH/SOL market opened, we assume ETH/SOL
        moved roughly BTC_CORR_WEIGHT * X% in the same direction (crypto beta).
        Then apply BS with the BTC-derived vol, scaled down by the same weight.
        """
        if state.chainlink_btc <= 0:
            return None

        # Pin BTC at ETH/SOL market open if we haven't yet
        if slug not in self._btc_at_market_open_eth_sol:
            self._btc_at_market_open_eth_sol[slug] = state.chainlink_btc
            return None  # no signal on the first tick — need BTC to move

        btc_open = self._btc_at_market_open_eth_sol[slug]
        if btc_open <= 0:
            return None

        # Proxy "implied current ETH/SOL" as a fraction of the BTC move.
        # Since we don't know the absolute ETH/SOL price, we work in log-return
        # space: log(S_now / S_open) ≈ BTC_CORR_WEIGHT * log(BTC_now / BTC_open).
        try:
            btc_logret = math.log(state.chainlink_btc / btc_open)
        except (ValueError, ZeroDivisionError):
            return None

        proxy_logret = BTC_CORR_WEIGHT * btc_logret

        # Use BS directly on the log-return instead of absolute prices.
        interval_s = self._interval_seconds.get(mkt.interval, 300)
        # Residual vol: part of variance NOT explained by BTC + a scale for
        # the remaining window. We use the BTC per-interval vol scaled UP a
        # bit to account for ETH/SOL having higher realized vol than BTC.
        btc_sigma = self._vol.sigma_per_interval(interval_s)
        sigma = max(btc_sigma * 1.3, 0.002)

        tau = max(mkt.time_remaining_frac, 1e-4)
        s_sqrt_tau = sigma * math.sqrt(tau)
        if s_sqrt_tau < 1e-6:
            return None

        # P(YES) = P(ETH_T >= ETH_open) = P(log(ETH_T/ETH_open) >= 0)
        # given log(ETH_T/ETH_open) = log(ETH_now/ETH_open) + log(ETH_T/ETH_now)
        # ≈ proxy_logret + N(-sigma^2*tau/2, sigma^2*tau)
        d2 = (proxy_logret - s_sqrt_tau * s_sqrt_tau * 0.5) / s_sqrt_tau
        p = _standard_normal_cdf(d2)
        return max(0.02, min(0.98, p))

    # ── Exits ────────────────────────────────────────────────────────────────

    def _try_exits(
        self, slug: str, mkt: MarketView, state: MarketState
    ) -> list[Order]:
        """
        Close positions when the edge has closed.

        If we're long YES and the market has moved up so the mid is now close
        to our model fair (delta < EXIT_EDGE), take profits. Same symmetric
        logic for NO.
        """
        pos = state.positions.get(slug)
        if not pos:
            return []

        if _is_hedged_complete_set(pos):
            return []

        if not ENABLE_DIRECTIONAL_EXITS:
            return []

        # Exit cooldown — don't re-queue a sell while a previous one is
        # still in flight. Without this we get 100s of 'no liquidity at limit'
        # rejections.
        last_exit = self._last_exit_tick.get(slug, -10_000)
        if state.timestamp - last_exit < self._exit_cooldown_s:
            return []

        orders: list[Order] = []
        asset = _asset_from_slug(slug)

        # Compute fair — use same path as directional so numbers match
        if asset == ASSET_BTC:
            fair = self._btc_fair_value(slug, mkt, state)
        elif asset in (ASSET_ETH, ASSET_SOL):
            fair = self._corr_fair_value(slug, mkt, state, asset)
        else:
            return []
        if fair is None:
            return []

        market_mid = mkt.yes_price if mkt.yes_price > 0 else (mkt.yes_bid + mkt.yes_ask) / 2
        if market_mid <= 0:
            return []

        delta = fair - market_mid

        # Sell YES: we bought because delta > edge. Exit if delta is now
        # small/negative (market caught up or overshot).
        if pos.yes_shares > 0 and delta < EXIT_EDGE:
            # Only exit if bid is reasonable
            if mkt.yes_bid > 0.05:
                # Don't dump all at once if book is thin — cap at 70% of top bid
                top_bid_size = mkt.yes_book.bids[0].size if mkt.yes_book.bids else 0.0
                size = min(pos.yes_shares, top_bid_size * 0.7)
                if size >= 5:
                    orders.append(Order(
                        market_slug=slug,
                        token=Token.YES,
                        side=Side.SELL,
                        size=size,
                        limit_price=_clip_limit_price(mkt.yes_bid),
                    ))
                    self._last_exit_tick[slug] = state.timestamp

        # Sell NO: we bought NO because delta < -edge. Exit if delta is now
        # bigger/positive.
        if pos.no_shares > 0 and delta > -EXIT_EDGE:
            if mkt.no_bid > 0.05:
                top_bid_size = mkt.no_book.bids[0].size if mkt.no_book.bids else 0.0
                size = min(pos.no_shares, top_bid_size * 0.7)
                if size >= 5:
                    orders.append(Order(
                        market_slug=slug,
                        token=Token.NO,
                        side=Side.SELL,
                        size=size,
                        limit_price=_clip_limit_price(mkt.no_bid),
                    ))
                    self._last_exit_tick[slug] = state.timestamp

        return orders

    # ── Callbacks ────────────────────────────────────────────────────────────

    def on_fill(self, fill: Fill) -> None:
        """Track per-market cost so we can enforce PER_MARKET_MAX_COST."""
        if fill.side == Side.BUY:
            self._cost_by_market[fill.market_slug] = (
                self._cost_by_market.get(fill.market_slug, 0.0) + fill.cost
            )
        else:
            # SELL reduces cost basis
            self._cost_by_market[fill.market_slug] = max(
                0.0,
                self._cost_by_market.get(fill.market_slug, 0.0) - fill.cost,
            )

    def on_settlement(self, settlement: Settlement) -> None:
        """Free per-market state once market is done."""
        self._cost_by_market.pop(settlement.market_slug, None)
        self._arb_entries.pop(settlement.market_slug, None)
        self._directional_side.pop(settlement.market_slug, None)
        self._btc_at_market_open.pop(settlement.market_slug, None)
        self._btc_at_market_open_eth_sol.pop(settlement.market_slug, None)
        self._last_entry_tick.pop(settlement.market_slug, None)
        self._last_exit_tick.pop(settlement.market_slug, None)
        self._last_arb_tick.pop(settlement.market_slug, None)
