"""Tests for market_manager module."""

import pytest

from backtester.data_loader import TickData
from backtester.market_manager import MarketManager
from backtester.strategy import MarketLifecycle, MarketStatus, Settlement, Token
from tests.conftest import (
    BASE_TS,
    BTC_OPEN,
    MARKET_5M_END,
    MARKET_5M_SLUG,
    MARKET_5M_START,
    MARKET_15M_END,
    MARKET_15M_SLUG,
    MARKET_15M_START,
)


@pytest.fixture
def manager(market_5m_lifecycle, market_15m_lifecycle, settlement_5m_yes, settlement_15m_no):
    return MarketManager(
        lifecycles=[market_5m_lifecycle, market_15m_lifecycle],
        settlements={
            MARKET_5M_SLUG: settlement_5m_yes,
            MARKET_15M_SLUG: settlement_15m_no,
        },
    )


class TestMarketManager:
    def test_initial_state(self, manager):
        """Both markets start as UPCOMING."""
        for slug, lc in manager.lifecycles.items():
            assert lc.status == MarketStatus.UPCOMING

    def test_market_becomes_active(self, manager):
        """5m market should become active at its start_ts."""
        views = manager.update(MARKET_5M_START)
        assert MARKET_5M_SLUG in views
        assert manager.lifecycles[MARKET_5M_SLUG].status == MarketStatus.ACTIVE
        assert views[MARKET_5M_SLUG].chainlink_open == pytest.approx(BTC_OPEN)

    def test_market_not_active_before_start(self, manager):
        """5m market should not be active before start."""
        views = manager.update(MARKET_5M_START - 1)
        assert MARKET_5M_SLUG not in views

    def test_market_settles_at_end(self, manager):
        """5m market should settle when time reaches end_ts."""
        # First make it active
        manager.update(MARKET_5M_START)
        # Then settle it
        views = manager.update(MARKET_5M_END)
        assert MARKET_5M_SLUG not in views
        settled = manager.get_settled_this_tick()
        assert len(settled) == 1
        assert settled[0].market_slug == MARKET_5M_SLUG
        assert settled[0].outcome == Token.YES

    def test_both_markets_lifecycle(self, manager):
        """Test full lifecycle of both markets."""
        # Before everything
        views = manager.update(BASE_TS - 1)
        assert len(views) == 0

        # 5m active
        views = manager.update(BASE_TS + 100)
        assert MARKET_5M_SLUG in views
        assert MARKET_15M_SLUG not in views

        # 5m settles, 15m becomes active
        views = manager.update(MARKET_5M_END)
        settled = manager.get_settled_this_tick()
        assert len(settled) == 1  # 5m settled

        # 15m active (need to call update for the tick after settlement)
        views = manager.update(MARKET_15M_START + 1)
        assert MARKET_15M_SLUG in views

        # 15m settles
        views = manager.update(MARKET_15M_END)
        settled = manager.get_settled_this_tick()
        assert len(settled) == 1
        assert settled[0].outcome == Token.NO

    def test_settled_this_tick_cleared(self, manager):
        """Settled list is cleared between ticks."""
        manager.update(MARKET_5M_START)
        manager.update(MARKET_5M_END)
        assert len(manager.get_settled_this_tick()) == 1

        # Next tick: settled list should be empty
        manager.update(MARKET_5M_END + 1)
        assert len(manager.get_settled_this_tick()) == 0

    def test_is_market_active(self, manager):
        manager.update(MARKET_5M_START + 10)
        assert manager.is_market_active(MARKET_5M_SLUG)
        assert not manager.is_market_active(MARKET_15M_SLUG)

    def test_enrich_views(self, manager):
        """Enriching views adds book and price data from tick."""
        views = manager.update(MARKET_5M_START + 10)

        tick = TickData(ts_sec=MARKET_5M_START + 10)
        from tests.conftest import make_yes_book, make_no_book
        tick.order_books[MARKET_5M_SLUG] = {
            "yes_book": make_yes_book(0.55),
            "no_book": make_no_book(0.55),
        }
        tick.market_prices[MARKET_5M_SLUG] = {
            "yes_price": 0.55,
            "no_price": 0.45,
            "yes_bid": 0.53,
            "yes_ask": 0.57,
            "no_bid": 0.43,
            "no_ask": 0.47,
        }

        enriched = manager.enrich_views(views, tick)
        view = enriched[MARKET_5M_SLUG]
        assert view.yes_price == 0.55
        assert view.no_price == 0.45
        assert view.yes_book.best_bid > 0
