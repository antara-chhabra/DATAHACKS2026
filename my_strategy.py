from __future__ import annotations
import math
from collections import deque
from backtester.strategy import (
    BaseStrategy, Fill, MarketState, Order,
    Settlement, Side, Token
)
# ─────────────────────────────────────────────
# CONFIG (balanced for 15–20%)
# ─────────────────────────────────────────────
_VOL = {
    ("BTC","5m"):0.004, ("BTC","15m"):0.007, ("BTC","hourly"):0.013,
    ("ETH","5m"):0.005, ("ETH","15m"):0.009, ("ETH","hourly"):0.016,
}
_MAX_ENTRY = {"5m":280,"15m":360,"hourly":440}
_MIN_BOOK_DEPTH = 45.0
# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _asset(slug):
    s = slug.lower()
    if s.startswith(("btc-","bitcoin-")): return "BTC"
    if s.startswith(("eth-","ethereum-")): return "ETH"
    return "SOL"
def _interval(slug):
    s = slug.lower()
    if "-5m-" in s: return "5m"
    if "-15m-" in s: return "15m"
    return "hourly"
def _ncdf(x):
    return 0.5*(1+math.erf(x/math.sqrt(2)))
def _fair_prob(spot,open_,vol,frac):
    if spot<=0 or open_<=0: return 0.5
    tau=max(frac,0.001)
    sigma=vol*math.sqrt(tau)
    if sigma<1e-8:
        return 0.99 if spot>=open_ else 0.01
    d2=math.log(spot/open_)/sigma - sigma/2
    return max(0.01,min(0.99,_ncdf(d2)))
def _imbalance(book):
    b,a=book.total_bid_size,book.total_ask_size
    t=b+a
    return (b-a)/t if t>1 else 0.0
# ─────────────────────────────────────────────
# STRATEGY
# ─────────────────────────────────────────────
class AggressiveEdgeV3(BaseStrategy):
    def __init__(self):
        # tuned for scale, not overfit
        self.arb_edge = 0.006
        self.min_edge = 0.045
        self.cash_frac = 0.92
        self.momentum_threshold = 0.0002
        self._open = {}
        self._arb_count = {}
        self._entered = set()
        self._entry_price = {}
        # history for correlation + momentum
        self._hist = {
            "BTC": deque(maxlen=200),
            "ETH": deque(maxlen=200),
        }
        self._last_prices = {}
    # ─────────────────────────────────────────
    # DATA
    # ─────────────────────────────────────────
    def _cl(self, state, a):
        return {
            "BTC":state.chainlink_btc,
            "ETH":state.chainlink_eth,
            "SOL":state.chainlink_sol
        }[a]
    def _mid(self, state, a):
        return {
            "BTC":state.btc_mid,
            "ETH":state.eth_mid,
            "SOL":state.sol_mid
        }[a]
    def _momentum(self, a):
        h=self._hist[a]
        if len(h)<20: return 0.0
        return (h[-1]-h[-20])/h[-20]
    def _correlation_boost(self):
        # simple BTC/ETH agreement signal
        if len(self._hist["BTC"])<20 or len(self._hist["ETH"])<20:
            return 0.0
        btc_m = (self._hist["BTC"][-1]-self._hist["BTC"][-20])/self._hist["BTC"][-20]
        eth_m = (self._hist["ETH"][-1]-self._hist["ETH"][-20])/self._hist["ETH"][-20]
        if btc_m*eth_m > 0:  # same direction
            return 0.01
        return -0.01
    def _cash(self,state):
        return state.cash*self.cash_frac
    def _remaining(self,slug,token,state):
        pos=state.positions.get(slug)
        if not pos: return 500
        current=pos.yes_shares if token==Token.YES else pos.no_shares
        return max(0,500-current)
    # ─────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────
    def on_tick(self,state:MarketState):
        orders=[]
        cash=self._cash(state)
        # update history
        for a in ["BTC","ETH"]:
            p=self._mid(state,a)
            if p>0:
                self._hist[a].append(p)
        corr_boost = self._correlation_boost()
        for slug,m in state.markets.items():
            asset=_asset(slug)
            interval=_interval(slug)
            # SOL directional disabled
            allow_dir = asset!="SOL"
            cl=self._cl(state,asset)
            if slug not in self._open and cl>0:
                self._open[slug]=cl
            cl_open=self._open.get(slug,0)
            if cl_open<=0: continue
            yes,no=m.yes_ask,m.no_ask
            if yes<=0 or no<=0: continue
            # ───────────────────────── ARB
            combined=yes+no
            edge=1-combined
            count=self._arb_count.get(slug,0)
            if edge>=self.arb_edge and count<8:
                size=min(
                    240,
                    self._remaining(slug,Token.YES,state),
                    self._remaining(slug,Token.NO,state),
                    cash/combined if combined>0 else 0
                )
                if size>=20:
                    orders.append(Order(slug,Token.YES,Side.BUY,size,yes))
                    orders.append(Order(slug,Token.NO,Side.BUY,size,no))
                    self._arb_count[slug]=count+1
                    cash-=size*combined
                    continue
            # ───────────────────────── DIRECTIONAL
            if not allow_dir:
                continue
            if m.time_remaining_frac>0.85 or m.time_remaining_frac<0.03:
                continue
            fair=_fair_prob(
                cl,cl_open,
                _VOL.get((asset,interval),0.006),
                m.time_remaining_frac
            )
            mom=self._momentum(asset)
            if abs(mom)<self.momentum_threshold:
                continue
            # correlation-adjusted edge
            adj_edge = self.min_edge + corr_boost
            if cl>cl_open:
                token=Token.YES
                ask=yes
                edge_d = fair-ask
                if mom<0: continue
                if m.yes_book.total_ask_size<_MIN_BOOK_DEPTH: continue
            elif cl<cl_open:
                token=Token.NO
                ask=no
                edge_d = (1-fair)-ask
                if mom>0: continue
                if m.no_book.total_ask_size<_MIN_BOOK_DEPTH: continue
            else:
                continue
            if edge_d < adj_edge:
                continue
            # smarter re-entry (ONLY if edge improved)
            if slug in self._entered:
                prev=self._entry_price.get(slug,ask)
                if edge_d < self.min_edge*1.5:
                    continue
            if ask>0.84:
                continue
            size=min(
                _MAX_ENTRY.get(interval,250),
                self._remaining(slug,token,state),
                cash/ask if ask>0 else 0
            )
            if size<20:
                continue
            orders.append(Order(
                slug,
                token,
                Side.BUY,
                size,
                min(ask+0.012,0.96)
            ))
            self._entered.add(slug)
            self._entry_price[slug]=ask
            cash-=size*ask
        return orders
    # ─────────────────────────────────────────
    def on_settlement(self,settlement:Settlement):
        slug=settlement.market_slug
        self._open.pop(slug,None)
        self._arb_count.pop(slug,None)
        self._entered.discard(slug)
        self._entry_price.pop(slug,None)
    def on_fill(self,fill:Fill):
        pass
