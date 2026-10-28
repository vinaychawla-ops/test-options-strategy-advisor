"""Tests for the shared statistics module (lognormal probs, expected move, payoffs)."""

import math

import pytest
from statistics import (
    avg_atm_iv,
    bear_put_payoff,
    bull_call_payoff,
    expected_move,
    ndist,
    payoff_label,
    prob_above,
    prob_below,
    resolve_dte,
    short_put_label,
    short_put_payoff,
    straddle_payoff,
)


# ── Normal CDF ────────────────────────────────────────────────────────


class TestNdist:
    def test_known_values(self):
        assert ndist(0.0) == pytest.approx(0.5)
        assert ndist(1.0) == pytest.approx(0.8413447461, rel=1e-9)
        assert ndist(-1.0) == pytest.approx(0.1586552539, rel=1e-9)

    def test_monotonic(self):
        assert ndist(0.5) > ndist(0.0) > ndist(-0.5)


# ── Lognormal probabilities ───────────────────────────────────────────


class TestProbabilities:
    def test_atm_coin_flip(self):
        # level == spot -> z = 0 -> 50/50
        assert prob_above(100, 100, 0.20, 30) == pytest.approx(0.5, abs=1e-6)
        assert prob_below(100, 100, 0.20, 30) == pytest.approx(0.5, abs=1e-6)

    def test_above_and_below_sum_to_one(self):
        p = prob_above(110, 100, 0.25, 30)
        assert p + prob_below(110, 100, 0.25, 30) == pytest.approx(1.0)

    def test_higher_level_lower_prob(self):
        assert prob_above(120, 100, 0.25, 30) < prob_above(110, 100, 0.25, 30)

    def test_more_dte_wider_distribution(self):
        # More time to expiry pushes probability away from spot toward extremes
        p_short = prob_above(115, 100, 0.25, 10)
        p_long = prob_above(115, 100, 0.25, 60)
        assert p_long > p_short

    def test_spcx_30d_reference(self):
        # SPCX 30 DTE: spot 132.78, IV 0.76, 32 days. P(below 125) ~ 39.4%
        assert prob_below(125, 132.78, 0.76, 32) == pytest.approx(0.394, abs=0.01)


# ── Expected move ─────────────────────────────────────────────────────


class TestExpectedMove:
    def test_known(self):
        move, lo, hi = expected_move(100, 0.20, 365)
        assert move == pytest.approx(20.0, rel=1e-6)
        assert lo == pytest.approx(80.0)
        assert hi == pytest.approx(120.0)

    def test_spcx_30d(self):
        move, lo, hi = expected_move(132.78, 0.76, 32)
        assert move == pytest.approx(29.88, abs=0.05)
        assert lo == pytest.approx(102.90, abs=0.05)
        assert hi == pytest.approx(162.66, abs=0.05)

    def test_zero_dte_no_op(self):
        move, lo, hi = expected_move(100, 0.2, 0)
        assert move == 0.0


# ── avg_atm_iv / resolve_dte ──────────────────────────────────────────


class TestHelpers:
    def test_avg_atm_iv_nearest_four(self):
        data = {
            "stock_price": 100.0,
            "options": [
                {"strike": 90, "iv": 0.30},
                {"strike": 95, "iv": 0.25},
                {"strike": 100, "iv": 0.20},
                {"strike": 105, "iv": 0.22},
                {"strike": 110, "iv": 0.28},
            ],
        }
        # 4 nearest to 100: strikes 100, 95, 105, 90 -> avg (0.20+0.25+0.22+0.30)/4
        assert avg_atm_iv(data) == pytest.approx(0.2425)

    def test_avg_atm_iv_missing(self):
        assert avg_atm_iv({"stock_price": 100, "options": [{"strike": 100, "iv": None}]}) is None
        assert avg_atm_iv({"stock_price": 100}) is None

    def test_resolve_dte_from_key(self):
        assert resolve_dte({"dte": 32}, None) == 32

    def test_resolve_dte_from_expiration(self):
        from datetime import date, timedelta
        exp = (date.today() + timedelta(days=45)).isoformat()
        assert resolve_dte({"expiration": exp}) == 45

    def test_resolve_dte_fallback(self):
        assert resolve_dte({}, 30) == 30


# ── Payoff functions ──────────────────────────────────────────────────


class TestPayoffs:
    def test_straddle(self):
        assert straddle_payoff(135, 133, 10.30) == pytest.approx(-8.30)
        assert straddle_payoff(150, 133, 10.30) == pytest.approx(6.70)

    def test_bull_call(self):
        # buy 130 call, sell 140 call, net debit 4.13
        assert bull_call_payoff(110, 130, 140, 4.13) == pytest.approx(-4.13)
        assert bull_call_payoff(135, 130, 140, 4.13) == pytest.approx(0.87)
        assert bull_call_payoff(160, 130, 140, 4.13) == pytest.approx(5.87)

    def test_bear_put(self):
        # buy 135 put, sell 130 put, net debit 2.83
        assert bear_put_payoff(110, 135, 130, 2.83) == pytest.approx(2.17)
        assert bear_put_payoff(135, 135, 130, 2.83) == pytest.approx(-2.83)

    def test_short_put(self):
        # sell 125 put for 7.78 credit
        assert short_put_payoff(130, 125, 7.78) == pytest.approx(7.78)
        assert short_put_payoff(110, 125, 7.78) == pytest.approx(-7.22)


# ── Labels ────────────────────────────────────────────────────────────


class TestLabels:
    def test_gain_lose(self):
        assert payoff_label(1.0) == "Gain"
        assert payoff_label(-1.0) == "Lose"
        assert payoff_label(0.0) == "Partial Gain"

    def test_max_gain_loss(self):
        assert payoff_label(5.87, max_profit=5.87) == "Max Gain"
        assert payoff_label(-4.13, max_loss=-4.13) == "Max Loss"

    def test_short_put(self):
        assert short_put_label(7.78, 7.78) == "Keep Premium"
        assert short_put_label(-7.22, 7.78) == "Assigned"
        assert short_put_label(3.0, 7.78) == "Partial Gain"
