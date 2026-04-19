"""Tests for scoring module."""

import pytest

from backtester.engine import BacktestResult
from backtester.portfolio import PortfolioSnapshot
from backtester.scoring import ScoreCard, _compute_max_drawdown, _compute_sharpe, compute_score
from backtester.strategy import Fill, Settlement, Side, Token


def _make_snapshots(values: list[float], start_ts: int = 0) -> list[PortfolioSnapshot]:
    """Create portfolio snapshots from a list of values."""
    return [
        PortfolioSnapshot(
            timestamp=start_ts + i,
            cash=v,
            positions={},
            total_value=v,
            realized_pnl=v - values[0],
            unrealized_pnl=0.0,
        )
        for i, v in enumerate(values)
    ]


class TestSharpe:
    def test_constant_returns(self):
        """Constant portfolio value -> zero Sharpe (no variance)."""
        snapshots = _make_snapshots([10000] * 100)
        assert _compute_sharpe(snapshots) == 0.0

    def test_positive_returns(self):
        """Monotonically increasing -> positive Sharpe."""
        values = [10000 + i * 0.1 for i in range(1000)]
        snapshots = _make_snapshots(values)
        assert _compute_sharpe(snapshots) > 0

    def test_negative_returns(self):
        """Monotonically decreasing -> negative Sharpe."""
        values = [10000 - i * 0.1 for i in range(1000)]
        snapshots = _make_snapshots(values)
        assert _compute_sharpe(snapshots) < 0

    def test_empty_snapshots(self):
        assert _compute_sharpe([]) == 0.0

    def test_single_snapshot(self):
        snapshots = _make_snapshots([10000])
        assert _compute_sharpe(snapshots) == 0.0


class TestMaxDrawdown:
    def test_no_drawdown(self):
        """Monotonically increasing -> zero drawdown."""
        values = [10000 + i for i in range(100)]
        snapshots = _make_snapshots(values)
        dd, dd_pct = _compute_max_drawdown(snapshots)
        assert dd == 0.0
        assert dd_pct == 0.0

    def test_simple_drawdown(self):
        """Clear peak-to-trough drawdown."""
        values = [10000, 10100, 10200, 10000, 9800, 10100]
        snapshots = _make_snapshots(values)
        dd, dd_pct = _compute_max_drawdown(snapshots)
        assert dd == 400.0  # 10200 -> 9800
        assert dd_pct == pytest.approx(400.0 / 10200 * 100, rel=1e-4)

    def test_empty(self):
        dd, dd_pct = _compute_max_drawdown([])
        assert dd == 0.0


class TestComputeScore:
    def test_basic_score(self):
        result = BacktestResult(
            strategy_name="TestStrategy",
            start_ts=0,
            end_ts=1000,
            starting_cash=10000,
            final_cash=10500,
            final_portfolio_value=10500,
            total_pnl=500,
            total_trades=10,
            total_settlements=5,
            total_rejected=2,
            portfolio_snapshots=_make_snapshots([10000 + i * 0.5 for i in range(1000)]),
            fills=[],
            settlements=[],
            elapsed_seconds=1.5,
        )
        score = compute_score(result)

        assert score.strategy_name == "TestStrategy"
        assert score.total_pnl == 500
        assert score.return_pct == 5.0
        assert score.competition_score == 500
        assert score.total_trades == 10

    def test_no_trades_score(self):
        result = BacktestResult(
            strategy_name="Idle",
            start_ts=0, end_ts=100,
            starting_cash=10000, final_cash=10000,
            final_portfolio_value=10000, total_pnl=0,
            total_trades=0, total_settlements=0, total_rejected=0,
            portfolio_snapshots=_make_snapshots([10000] * 10),
            fills=[], settlements=[], elapsed_seconds=0.1,
        )
        score = compute_score(result)
        assert score.total_pnl == 0
        assert score.sharpe_ratio == 0
        assert score.win_rate == 0
