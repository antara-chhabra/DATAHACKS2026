"""Tests for portfolio module."""

import pytest

from backtester.portfolio import Portfolio
from backtester.strategy import Fill, MarketView, Settlement, Side, Token
from tests.conftest import (
    MARKET_5M_END,
    MARKET_5M_SLUG,
    MARKET_5M_START,
    MARKET_15M_SLUG,
    make_no_book,
    make_yes_book,
)


@pytest.fixture
def portfolio():
    return Portfolio(starting_cash=10_000.0)


class TestPortfolio:
    def test_initial_state(self, portfolio):
        assert portfolio.cash == 10_000.0
        assert portfolio.realized_pnl == 0.0
        assert portfolio.total_fills == 0

    def test_buy_reduces_cash(self, portfolio):
        fill = Fill(
            market_slug=MARKET_5M_SLUG,
            token=Token.YES,
            side=Side.BUY,
            size=100,
            avg_price=0.50,
            cost=50.0,
            timestamp=100,
        )
        portfolio.apply_fill(fill)
        assert portfolio.cash == 9_950.0
        pos = portfolio.get_position(MARKET_5M_SLUG)
        assert pos.yes_shares == 100
        assert pos.cost_basis == 50.0

    def test_sell_increases_cash(self, portfolio):
        # First buy
        buy = Fill(MARKET_5M_SLUG, Token.YES, Side.BUY, 100, 0.50, 50.0, 100)
        portfolio.apply_fill(buy)

        # Then sell
        sell = Fill(MARKET_5M_SLUG, Token.YES, Side.SELL, 50, 0.55, 27.5, 200)
        portfolio.apply_fill(sell)

        assert portfolio.cash == 9_950.0 + 27.5
        pos = portfolio.get_position(MARKET_5M_SLUG)
        assert pos.yes_shares == 50

    def test_settlement_yes_wins(self, portfolio):
        """YES outcome: yes_shares pay $1, no_shares pay $0."""
        buy = Fill(MARKET_5M_SLUG, Token.YES, Side.BUY, 100, 0.50, 50.0, 100)
        portfolio.apply_fill(buy)

        settlement = Settlement(
            market_slug=MARKET_5M_SLUG,
            interval="5m",
            outcome=Token.YES,
            start_ts=MARKET_5M_START,
            end_ts=MARKET_5M_END,
        )
        pnl = portfolio.apply_settlement(settlement)

        assert pnl == 50.0  # 100 shares * $1 - $50 cost = $50 profit
        assert portfolio.cash == 10_000.0 + 50.0  # started with 10k, -50 buy, +100 payout
        pos = portfolio.get_position(MARKET_5M_SLUG)
        assert pos.yes_shares == 0.0

    def test_settlement_no_wins(self, portfolio):
        """NO outcome: no_shares pay $1, yes_shares pay $0."""
        buy = Fill(MARKET_5M_SLUG, Token.YES, Side.BUY, 100, 0.50, 50.0, 100)
        portfolio.apply_fill(buy)

        settlement = Settlement(
            market_slug=MARKET_5M_SLUG,
            interval="5m",
            outcome=Token.NO,
            start_ts=MARKET_5M_START,
            end_ts=MARKET_5M_END,
        )
        pnl = portfolio.apply_settlement(settlement)

        assert pnl == -50.0  # YES shares worthless, lost the $50
        assert portfolio.cash == 9_950.0  # only get back nothing

    def test_no_shares_payout(self, portfolio):
        """Buying NO shares should pay when NO wins."""
        buy = Fill(MARKET_5M_SLUG, Token.NO, Side.BUY, 100, 0.45, 45.0, 100)
        portfolio.apply_fill(buy)

        settlement = Settlement(
            market_slug=MARKET_5M_SLUG,
            interval="5m",
            outcome=Token.NO,
            start_ts=MARKET_5M_START,
            end_ts=MARKET_5M_END,
        )
        pnl = portfolio.apply_settlement(settlement)

        assert pnl == 55.0  # 100 * $1 - $45 = $55 profit

    def test_mark_to_market(self, portfolio):
        buy = Fill(MARKET_5M_SLUG, Token.YES, Side.BUY, 100, 0.50, 50.0, 100)
        portfolio.apply_fill(buy)

        views = {
            MARKET_5M_SLUG: MarketView(
                market_slug=MARKET_5M_SLUG,
                interval="5m",
                start_ts=MARKET_5M_START,
                end_ts=MARKET_5M_END,
                time_remaining_s=150,
                time_remaining_frac=0.5,
                yes_price=0.60,  # price went up
                no_price=0.40,
            )
        }
        total = portfolio.mark_to_market(views)
        # Cash: 9950 + 100 shares * 0.60 = 9950 + 60 = 10010
        assert total == pytest.approx(10_010.0)

    def test_snapshot(self, portfolio):
        buy = Fill(MARKET_5M_SLUG, Token.YES, Side.BUY, 100, 0.50, 50.0, 100)
        portfolio.apply_fill(buy)

        views = {
            MARKET_5M_SLUG: MarketView(
                market_slug=MARKET_5M_SLUG,
                interval="5m",
                start_ts=MARKET_5M_START,
                end_ts=MARKET_5M_END,
                time_remaining_s=150,
                time_remaining_frac=0.5,
                yes_price=0.55,
                no_price=0.45,
            )
        }
        snap = portfolio.snapshot(200, views)
        assert snap.timestamp == 200
        assert snap.cash == 9_950.0
        assert snap.total_value == pytest.approx(9_950.0 + 55.0)
        assert MARKET_5M_SLUG in snap.positions

    def test_complete_set_arb(self, portfolio):
        """Buying YES+NO = guaranteed $1 payout regardless of outcome."""
        buy_yes = Fill(MARKET_5M_SLUG, Token.YES, Side.BUY, 100, 0.48, 48.0, 100)
        buy_no = Fill(MARKET_5M_SLUG, Token.NO, Side.BUY, 100, 0.48, 48.0, 100)
        portfolio.apply_fill(buy_yes)
        portfolio.apply_fill(buy_no)

        # Total cost: $96. Either outcome pays $100.
        settlement = Settlement(
            MARKET_5M_SLUG, "5m", Token.YES,
            MARKET_5M_START, MARKET_5M_END,
        )
        pnl = portfolio.apply_settlement(settlement)
        # YES wins: 100 yes shares * $1 = $100 payout. Cost was $96.
        assert pnl == 4.0  # $100 - $96
