"""Tests for fetch_oi_volume helpers (IV stats, percentile)."""

import numpy as np
import pandas as pd
import pytest

from scripts.fetch_oi_volume import (
    _avg_atm_iv,
    _patch,
    _percentile_of_score,
    compute_iv_stats,
)


class TestPercentileOfScore:
    def test_returns_none_for_empty(self):
        assert _percentile_of_score([], 5) is None
        assert _percentile_of_score(np.array([]), 5) is None
        assert _percentile_of_score(None, 5) is None

    def test_perfect_score(self):
        data = [1, 2, 3, 4, 5]
        assert _percentile_of_score(data, 5) == 100.0
        assert _percentile_of_score(data, 0) == 0.0

    def test_mid_value(self):
        data = [10, 20, 30, 40, 50]
        assert _percentile_of_score(data, 30) == 60.0  # 10,20,30 <= 30 → 3/5

    def test_numpy_array(self):
        data = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        result = _percentile_of_score(data, 0.25)
        assert result == 40.0  # 0.1, 0.2 <= 0.25 → 2/5


class TestAvgAtmIv:
    def test_returns_none_without_stock_price(self):
        assert _avg_atm_iv({"options": []}) is None

    def test_returns_none_without_options(self):
        assert _avg_atm_iv({"stock_price": 100}) is None

    def test_selects_nearest_strikes(self):
        data = {
            "stock_price": 100,
            "options": [
                {"strike": 90, "iv": 0.25},
                {"strike": 95, "iv": 0.28},
                {"strike": 100, "iv": 0.30},
                {"strike": 105, "iv": 0.32},
                {"strike": 110, "iv": 0.35},
            ],
        }
        result = _avg_atm_iv(data)
        # nearest 4: 95(0.28), 100(0.30), 105(0.32), 90(0.25)
        expected = (0.28 + 0.30 + 0.32 + 0.25) / 4
        assert result == pytest.approx(expected)

    def test_ignores_zero_iv(self):
        data = {
            "stock_price": 100,
            "options": [
                {"strike": 90, "iv": 0.0},
                {"strike": 95, "iv": 0.28},
                {"strike": 100, "iv": 0.30},
            ],
        }
        result = _avg_atm_iv(data)
        assert result == pytest.approx((0.28 + 0.30) / 2)


class TestComputeIvStats:
    def test_returns_none_for_missing_args(self):
        assert compute_iv_stats(None, 0.3) is None
        assert compute_iv_stats("SMH", None) is None
        assert compute_iv_stats("", 0.3) is None

    def test_returns_expected_keys(self, mocker):
        mock_hist = mocker.MagicMock()
        # Build 500 days of trending prices (enough for 30d rolling HV)
        rng = np.random.default_rng(42)
        prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 500)))
        mock_hist.empty = False
        mock_hist.__len__.return_value = 500
        mock_hist.__getitem__.side_effect = lambda key: (
            pd.Series(prices) if key == "Close" else mock_hist
        )
        mocker.patch(
            "scripts.fetch_oi_volume.Ticker",
            return_value=mocker.MagicMock(history=mocker.MagicMock(return_value=mock_hist)),
        )

        result = compute_iv_stats("TEST", 0.30)
        assert result is not None
        assert "iv_rank" in result
        assert "iv_percentile" in result
        assert "hv_high_52w" in result
        assert "hv_low_52w" in result
        assert "num_readings" in result
        assert 0 <= result["iv_rank"] <= 100
        assert 0 <= result["iv_percentile"] <= 100
        assert result["num_readings"] > 0
