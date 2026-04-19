"""Tests for hourly interval support in data_loader."""
import pytest
from backtester.data_loader import INTERVALS, parse_slug_lifecycle


class TestHourlyInterval:
    """Tests for hourly slug parsing."""

    def test_hourly_in_intervals(self):
        assert "hourly" in INTERVALS
        assert INTERVALS["hourly"]["seconds"] == 3600

    def test_parse_hourly_slug_pm(self):
        slug = "bitcoin-up-or-down-april-6-2026-5pm-et"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.market_slug == slug
        assert lc.interval == "hourly"
        assert lc.end_ts - lc.start_ts == 3600

    def test_parse_hourly_slug_am(self):
        slug = "bitcoin-up-or-down-march-26-2026-9am-et"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "hourly"
        assert lc.end_ts - lc.start_ts == 3600

    def test_parse_hourly_slug_12pm(self):
        slug = "bitcoin-up-or-down-april-1-2026-12pm-et"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "hourly"

    def test_parse_hourly_slug_12am(self):
        slug = "bitcoin-up-or-down-april-1-2026-12am-et"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "hourly"

    def test_parse_5m_slug_still_works(self):
        slug = "btc-updown-5m-1775001600"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "5m"
        assert lc.start_ts == 1775001600

    def test_parse_15m_slug_still_works(self):
        slug = "btc-updown-15m-1775001600"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "15m"

    def test_parse_sol_5m_slug(self):
        slug = "sol-updown-5m-1775001600"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "5m"
        assert lc.start_ts == 1775001600
        assert lc.end_ts == 1775001600 + 300

    def test_parse_eth_5m_slug(self):
        slug = "eth-updown-5m-1775001600"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "5m"
        assert lc.start_ts == 1775001600

    def test_parse_sol_15m_slug(self):
        slug = "sol-updown-15m-1775001600"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "15m"
        assert lc.end_ts == 1775001600 + 900

    def test_parse_eth_15m_slug(self):
        slug = "eth-updown-15m-1775001600"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "15m"

    def test_parse_solana_hourly_slug(self):
        slug = "solana-up-or-down-april-6-2026-5pm-et"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "hourly"
        assert lc.end_ts - lc.start_ts == 3600

    def test_parse_ethereum_hourly_slug(self):
        slug = "ethereum-up-or-down-march-26-2026-9am-et"
        lc = parse_slug_lifecycle(slug)
        assert lc is not None
        assert lc.interval == "hourly"

    def test_parse_unknown_slug(self):
        assert parse_slug_lifecycle("some-random-market") is None
