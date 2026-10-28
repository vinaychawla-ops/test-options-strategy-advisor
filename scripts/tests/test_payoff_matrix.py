"""Tests for the At-Expiry payoff matrix CLI."""

import json

import pytest
import payoff_matrix as pm


@pytest.fixture
def market_data():
    return {
        "stock_price": 132.78,
        "ticker": "TEST",
        "expiration": "2026-09-11",
        "dte": 32,
        "options": [
            {"strike": 125, "type": "call", "iv": 0.7420, "volume": 15, "open_interest": 201},
            {"strike": 130, "type": "call", "iv": 0.7486, "volume": 545, "open_interest": 519},
            {"strike": 135, "type": "call", "iv": 0.7600, "volume": 561, "open_interest": 232},
            {"strike": 140, "type": "call", "iv": 0.7623, "volume": 367, "open_interest": 608},
            {"strike": 125, "type": "put", "iv": 0.7545, "volume": 135, "open_interest": 493},
            {"strike": 130, "type": "put", "iv": 0.7533, "volume": 353, "open_interest": 712},
            {"strike": 135, "type": "put", "iv": 0.7636, "volume": 81, "open_interest": 84},
            {"strike": 140, "type": "put", "iv": 0.7709, "volume": 101, "open_interest": 44},
        ],
    }


STRATEGIES = [
    {"name": "Long Straddle 135", "type": "straddle", "strike": 135, "cost": 24.10},
    {"name": "Bull Call 130/140", "type": "bull_call",
     "strike_low": 130, "strike_high": 140, "cost": 4.13,
     "max_profit": 5.87, "max_loss": -4.13},
    {"name": "Bear Put 135/130", "type": "bear_put",
     "strike_low": 130, "strike_high": 135, "cost": 2.83,
     "max_profit": 2.17, "max_loss": -2.83},
    {"name": "Short Put 125", "type": "short_put", "strike": 125, "credit": 7.78},
]


class TestPayoffFor:
    def test_straddle(self):
        s = STRATEGIES[0]
        assert pm.payoff_for(s, 110) == pytest.approx(0.90)
        assert pm.payoff_for(s, 135) == pytest.approx(-24.10)

    def test_bull_call(self):
        s = STRATEGIES[1]
        assert pm.payoff_for(s, 160) == pytest.approx(5.87)
        assert pm.payoff_for(s, 125) == pytest.approx(-4.13)

    def test_bear_put(self):
        s = STRATEGIES[2]
        assert pm.payoff_for(s, 110) == pytest.approx(2.17)
        assert pm.payoff_for(s, 135) == pytest.approx(-2.83)

    def test_short_put(self):
        s = STRATEGIES[3]
        assert pm.payoff_for(s, 130) == pytest.approx(7.78)
        assert pm.payoff_for(s, 110) == pytest.approx(-7.22)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unknown strategy type"):
            pm.payoff_for({"type": "nope"}, 100)


class TestLabels:
    def test_short_put_assigned(self):
        s = STRATEGIES[3]
        assert pm.label_for(s, -7.22) == "Assigned"
        assert pm.label_for(s, 7.78) == "Keep Premium"

    def test_bull_call_max_gain(self):
        s = STRATEGIES[1]
        assert pm.label_for(s, 5.87) == "Max Gain"
        assert pm.label_for(s, -4.13) == "Max Loss"


class TestBreakevens:
    def test_straddle_two_bes(self):
        assert pm.breakevens(STRATEGIES[0]) == pytest.approx([110.90, 159.10])

    def test_bull_call(self):
        assert pm.breakevens(STRATEGIES[1]) == pytest.approx([134.13])

    def test_bear_put(self):
        assert pm.breakevens(STRATEGIES[2]) == pytest.approx([132.17])

    def test_short_put(self):
        assert pm.breakevens(STRATEGIES[3]) == pytest.approx([117.22])


class TestProbOfProfit:
    def test_straddle(self, market_data):
        # ~21% below 110.90 + ~21% above 159.10 -> ~42% total
        p = pm.prob_of_profit(STRATEGIES[0], market_data["stock_price"], 0.7551, 32)
        assert p == pytest.approx(0.42, abs=0.02)

    def test_bull_call(self, market_data):
        p = pm.prob_of_profit(STRATEGIES[1], market_data["stock_price"], 0.7551, 32)
        assert p == pytest.approx(0.48, abs=0.02)

    def test_missing_iv_returns_none(self, market_data):
        p = pm.prob_of_profit(STRATEGIES[0], market_data["stock_price"], None, 32)
        assert p is None


class TestMain:
    def test_text_output(self, market_data, tmp_path, capsys):
        md = tmp_path / "md.json"
        md.write_text(json.dumps(market_data))
        strat = tmp_path / "strat.json"
        strat.write_text(json.dumps(STRATEGIES))
        rc = pm.main(["--market-data", str(md), "--strategies", str(strat),
                      "--levels", "110", "125", "135", "160"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Long Straddle 135" in out
        assert "Max Gain" in out or "Keep Premium" in out

    def test_markdown_output(self, market_data, tmp_path, capsys):
        md = tmp_path / "md.json"
        md.write_text(json.dumps(market_data))
        strat = tmp_path / "strat.json"
        strat.write_text(json.dumps(STRATEGIES))
        rc = pm.main(["--market-data", str(md), "--strategies", str(strat),
                      "--levels", "110", "125", "135", "160", "--format", "markdown"])
        assert rc == 0
        assert "| Level |" in capsys.readouterr().out

    def test_probability_row(self, market_data, tmp_path, capsys):
        md = tmp_path / "md.json"
        md.write_text(json.dumps(market_data))
        strat = tmp_path / "strat.json"
        strat.write_text(json.dumps(STRATEGIES))
        rc = pm.main(["--market-data", str(md), "--strategies", str(strat),
                      "--levels", "110", "125", "135", "160", "--probability"])
        assert rc == 0
        assert "Prob of Profit" in capsys.readouterr().out

    def test_missing_files(self, tmp_path, capsys):
        rc = pm.main(["--market-data", str(tmp_path / "missing.json"),
                      "--strategies", str(tmp_path / "missing2.json")])
        assert rc == 1
