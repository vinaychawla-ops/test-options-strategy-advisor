"""Tests for the term-structure statistics CLI."""

import json

import pytest
import termstructure_stats as tss


@pytest.fixture
def sample_data():
    """Synthetic 2-expiry market-data dict (SPCX-like)."""
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


class TestAnalysis:
    def test_analyze_spot_iv_dte(self, sample_data):
        a = tss.analyze(sample_data)
        assert a["spot"] == 132.78
        assert a["dte"] == 32
        assert a["iv"] == pytest.approx(0.7564, abs=0.0005)

    def test_pc_ratios(self, sample_data):
        cv, pv, pc_vol, co, po, pc_oi = tss.pc_ratios(sample_data["options"])
        assert cv == 15 + 545 + 561 + 367
        assert pv == 135 + 353 + 81 + 101
        assert pc_vol == pytest.approx(pv / cv)
        assert pc_oi == pytest.approx(po / co)

    def test_per_strike_rows(self, sample_data):
        rows = tss.per_strike_rows(sample_data["options"])
        assert len(rows) == 4
        strike, cvol, pvol, coi, poi, civ, piv = rows[1]
        assert strike == 130
        assert civ == pytest.approx(0.7486)
        assert piv == pytest.approx(0.7533)

    def test_default_levels(self, sample_data):
        levels = tss.default_levels(sample_data["options"])
        assert 125 in levels and 140 in levels


class TestRendering:
    def test_text_contains_key_sections(self, sample_data):
        out = tss.render_text([tss.analyze(sample_data)], [125, 140])
        assert "Expected Move" in out
        assert "PUT/CALL RATIOS" in out
        assert "PER-STRIKE" in out
        assert "125.00" in out

    def test_markdown_tables(self, sample_data):
        out = tss.render_markdown([tss.analyze(sample_data)], [125, 140])
        assert "| Level | P(above) | P(below) |" in out
        assert "Per-Strike" in out


class TestMain:
    def test_main_returns_zero_and_prints(self, sample_data, tmp_path, capsys):
        p = tmp_path / "data.json"
        p.write_text(json.dumps(sample_data))
        rc = tss.main(["--market-data", str(p), "--levels", "125", "140"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Expected Move" in out

    def test_markdown_flag(self, sample_data, tmp_path, capsys):
        p = tmp_path / "data.json"
        p.write_text(json.dumps(sample_data))
        rc = tss.main(["--market-data", str(p), "--levels", "125", "--format", "markdown"])
        assert rc == 0
        assert "| Level | P(above) | P(below) |" in capsys.readouterr().out
