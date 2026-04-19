"""
MaxPnLHybrid_v2 — Aggressive multi-asset strategy for MAXIMUM total P&L
Uses BTC, ETH, SOL oracles + momentum + fair value + arb
"""

from collections import deque
import math

from backtester.strategy import (
    BaseStrategy,
    MarketState,
    Order,
    Side,
    Token,
)


def _standard_normal_cdf(x: float) -> float:
    """Approximate standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class MaxPnLHybrid_v2(BaseStrategy):
    """
    High-PnL strategy for the updated backtester (multi-asset support).
    - Priority 1: Complete-set arbitrage on any asset
    - Priority 2: Directional bets on BTC, ETH, or SOL using per-asset oracle + momentum
    """

    def __init__(self):
        self.market_opens: dict[str, float] = {}           # slug -> chainlink open price
        self.btc_history: deque[float] = deque(maxlen=300)
        self.eth_history: deque[float] = deque(maxlen=300)
        self.sol_history: deque[float] = deque(maxlen=300)
        self.traded: set[str] = set()

        self.min_arb_edge = 0.005
        self.direction_threshold = 0.06
        self.base_size = 110.0
        self.max_shares = 500.0

    def _get_asset_data(self, state: MarketState, slug: str):
        """Return correct mid, spread, chainlink for the asset."""
        slug_lower = slug.lower()
        if slug_lower.startswith(("btc-", "bitcoin-")):
            return state.btc_mid, state.btc_spread, state.chainlink_btc, "BTC"
        elif slug_lower.startswith(("eth-", "ethereum-")):
            return state.eth_mid, state.eth_spread, state.chainlink_eth, "ETH"
        elif slug_lower.startswith(("sol-", "solana-")):
            return state.sol_mid, state.sol_spread, state.chainlink_sol, "SOL"
        return state.btc_mid, state.btc_spread, state.chainlink_btc, "BTC"

    def on_tick(self, state: MarketState) -> list[Order]:
        orders: list[Order] = []

        # Update price histories
        if state.btc_mid > 0:
            self.btc_history.append(state.btc_mid)
        if state.eth_mid > 0:
            self.eth_history.append(state.eth_mid)
        if state.sol_mid > 0:
            self.sol_history.append(state.sol_mid)

        for slug, market in state.markets.items():
            if slug in self.traded:
                continue

            # Record open price
            if slug not in self.market_opens:
                _, _, chainlink, _ = self._get_asset_data(state, slug)
                if chainlink > 0:
                    self.market_opens[slug] = chainlink

            open_price = self.market_opens.get(slug)
            if not open_price:
                continue

            yes_ask = market.yes_ask
            no_ask = market.no_ask
            if yes_ask <= 0 or no_ask <= 0:
                continue

            # 1. COMPLETE-SET ARBITRAGE (risk-free)
            combined = yes_ask + no_ask
            arb_edge = 1.0 - combined
            if arb_edge >= self.min_arb_edge:
                size = min(self.base_size * 2, self.max_shares, state.cash / combined)
                if size >= 10:
                    orders.append(Order(slug, Token.YES, Side.BUY, size, yes_ask))
                    orders.append(Order(slug, Token.NO, Side.BUY, size, no_ask))
                    self.traded.add(slug)
                    continue

            # 2. DIRECTIONAL EDGE
            mid, spread, chainlink, asset = self._get_asset_data(state, slug)
            if chainlink <= 0 or mid <= 0:
                continue

            # Get correct history for momentum/vol
            if asset == "BTC":
                hist = self.btc_history
            elif asset == "ETH":
                hist = self.eth_history
            else:
                hist = self.sol_history

            if len(hist) < 60:
                continue

            recent = list(hist)
            momentum = (recent[-1] - recent[-60]) / recent[-60]

            # Rough vol
            rets = [(recent[i] - recent[i-1]) / recent[i-1] for i in range(1, len(recent))]
            vol = max(0.001, (sum(r*r for r in rets) / len(rets))**0.5)

            # Fair probability
            tau = max(market.time_remaining_frac, 0.001)
            log_m = math.log(chainlink / open_price)
            d2 = log_m / (vol * math.sqrt(tau)) - vol * math.sqrt(tau) / 2
            fair_prob = _standard_normal_cdf(d2)
            fair_prob = max(0.01, min(0.99, fair_prob))

            # Book imbalance
            imb = (market.yes_book.total_bid_size - market.yes_book.total_ask_size) / \
                  max(1.0, market.yes_book.total_bid_size + market.yes_book.total_ask_size)

            market_mid = market.yes_price
            edge = fair_prob - market_mid + (0.03 * momentum) + (0.02 * imb)

            if abs(edge) < self.direction_threshold:
                continue

            size_factor = min(1.0, abs(edge) * 8.0) * market.time_remaining_frac
            size = max(10.0, min(self.base_size * size_factor, self.max_shares))

            price = yes_ask if edge > 0 else no_ask
            if size * price > state.cash:
                continue

            if edge > 0:
                orders.append(Order(slug, Token.YES, Side.BUY, size, yes_ask))
            else:
                orders.append(Order(slug, Token.NO, Side.BUY, size, no_ask))

            self.traded.add(slug)

        return orders

    def on_fill(self, fill):
        pass

    def on_settlement(self, settlement):
        pass