#!/usr/bin/env python3
"""
GEX-to-HTML Report Generator

Reads GEX JSON files (produced by calculate_gex.py) and generates a
standalone, self-contained HTML report for easy visual analysis.

No data fetching — purely a formatting step.

Usage:
  C:\\Python314\\python.exe scripts\\gex_to_html.py --input output\\gex_avgo_30d.json
  C:\\Python314\\python.exe scripts\\gex_to_html.py --input output\\gex_avgo_30d.json --output report.html
  C:\\Python314\\python.exe scripts\\gex_to_html.py --input output\\gex_avgo_30d.json output\\gex_avgo_60d.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path


# =========================================================================
# Formatting helpers
# =========================================================================

def _fmt(value, none_placeholder="N/A"):
    if value is None:
        return none_placeholder
    return value


def _fmt_dollar(value):
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:+.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:+.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:+.1f}K"
    return f"${value:+.2f}"


def _fmt_dollar_no_sign(value):
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.2f}"


def _fmt_pct(value):
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _regime_class(regime):
    r = regime.lower()
    if "positive" in r:
        return "regime-positive"
    if "negative" in r:
        return "regime-negative"
    return "regime-neutral"


def _regime_emoji(regime):
    r = regime.lower()
    if "positive" in r:
        return "\u2191"  # up arrow
    if "negative" in r:
        return "\u2193"  # down arrow
    return "\u2194"  # left-right arrow


# =========================================================================
# CSS template
# =========================================================================

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f1f5f9;
  color: #1e293b;
  padding: 32px 16px;
  line-height: 1.5;
}
.container {
  max-width: 960px;
  margin: 0 auto;
}
.header {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  color: #f8fafc;
  padding: 28px 32px;
  border-radius: 12px;
  margin-bottom: 24px;
}
.header h1 { font-size: 24px; font-weight: 600; margin-bottom: 6px; letter-spacing: -0.3px; }
.header .subtitle { font-size: 14px; color: #94a3b8; }
.header .subtitle span { color: #e2e8f0; }
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.card {
  background: #fff;
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  border-left: 4px solid #cbd5e1;
}
.card .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-bottom: 4px; }
.card .value { font-size: 22px; font-weight: 700; }
.card .sublabel { font-size: 12px; color: #64748b; margin-top: 2px; }
.card-positive { border-left-color: #16a34a; }
.card-positive .value { color: #16a34a; }
.card-negative { border-left-color: #dc2626; }
.card-negative .value { color: #dc2626; }
.card-neutral { border-left-color: #d97706; }
.card-neutral .value { color: #d97706; }
.card-info { border-left-color: #2563eb; }
.card-info .value { color: #2563eb; }
.regime-banner {
  padding: 16px 24px;
  border-radius: 10px;
  margin-bottom: 24px;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}
.regime-positive { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.regime-negative { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.regime-neutral { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.regime-emoji { font-size: 22px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #334155; }
.strike-table-wrap {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  overflow-x: auto;
  margin-bottom: 24px;
}
.strike-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.strike-table th {
  background: #f8fafc;
  padding: 10px 14px;
  text-align: right;
  font-weight: 600;
  color: #475569;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}
.strike-table th:first-child { text-align: center; }
.strike-table td {
  padding: 8px 14px;
  text-align: right;
  border-bottom: 1px solid #f1f5f9;
  white-space: nowrap;
}
.strike-table td:first-child { text-align: center; font-weight: 600; color: #334155; }
.strike-table tr:hover { background: #f8fafc; }
.bar-cell { position: relative; min-width: 100px; }
.bar-container { display: flex; gap: 2px; height: 18px; align-items: center; }
.bar-wrapper { flex: 1; height: 14px; background: #f1f5f9; border-radius: 3px; overflow: hidden; }
.bar-call { height: 100%; background: #2563eb; border-radius: 3px; min-width: 2px; transition: width 0.2s; }
.bar-put { height: 100%; background: #dc2626; border-radius: 3px; min-width: 2px; transition: width 0.2s; }
.bar-label { font-size: 11px; color: #64748b; min-width: 60px; text-align: right; }
.value-positive { color: #16a34a; }
.value-negative { color: #dc2626; }
.value-neutral { color: #475569; }
.data-quality {
  background: #fff;
  border-radius: 10px;
  padding: 16px 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  margin-bottom: 24px;
  font-size: 13px;
  color: #64748b;
}
.data-quality strong { color: #334155; }
.footer {
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  padding: 16px;
}
.multi-expiry-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.tab {
  padding: 8px 18px;
  border-radius: 8px;
  background: #e2e8f0;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: default;
  text-decoration: none;
}
.tab.active { background: #1e293b; color: #f8fafc; }
.gex-chart {
  background: #fff;
  border-radius: 10px;
  padding: 16px 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  margin-bottom: 24px;
}
.gex-chart-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 3px 0;
  font-size: 13px;
}
.gex-chart-strike {
  min-width: 60px;
  font-weight: 600;
  color: #334155;
  text-align: right;
}
.gex-chart-bar-wrapper { flex: 1; height: 20px; display: flex; gap: 1px; }
.gex-chart-call {
  height: 100%;
  background: #2563eb;
  border-radius: 3px;
  min-width: 1px;
}
.gex-chart-put {
  height: 100%;
  background: #dc2626;
  border-radius: 3px;
  min-width: 1px;
}
.gex-chart-label { font-size: 11px; color: #64748b; min-width: 55px; text-align: right; }
"""


# =========================================================================
# HTML builder
# =========================================================================

def _build_metric_card(label, value, card_class, sublabel=None):
    sub = f'<div class="sublabel">{escape(sublabel)}</div>' if sublabel else ""
    return (
        f'<div class="card card-{card_class}">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        f'{sub}'
        f'</div>'
    )


def _build_regime_banner(regime):
    cls = _regime_class(regime)
    arrow = _regime_emoji(regime)
    return (
        f'<div class="regime-banner {cls}">'
        f'<span class="regime-emoji">{arrow}</span>'
        f'<span>{escape(regime)}</span>'
        f'</div>'
    )


def _build_strike_table(strikes, abs_total):
    if not strikes:
        return '<p style="color:#64748b;padding:16px;">No strike-level data available.</p>'

    abs_max = max(max(abs(s["call_gex"]), abs(s["put_gex"])) for s in strikes) if strikes else 1
    if abs_max <= 0:
        abs_max = 1

    rows = []
    for s in strikes:
        stk = s["strike"]
        cg = s["call_gex"]
        pg = s["put_gex"]
        ng = s["net_gex"]
        pct = s.get("pct_of_abs", 0)

        c_pct = abs(cg) / abs_max * 100 if abs_max > 0 else 0
        p_pct = abs(pg) / abs_max * 100 if abs_max > 0 else 0

        ng_class = "value-positive" if ng > 0 else ("value-negative" if ng < 0 else "value-neutral")

        rows.append(f"""\
<tr>
  <td>${stk:.2f}</td>
  <td><div class="bar-cell"><div class="bar-wrapper"><div class="bar-call" style="width:{c_pct:.1f}%"></div></div><div class="bar-label">{_fmt_dollar_no_sign(cg)}</div></div></td>
  <td><div class="bar-cell"><div class="bar-wrapper"><div class="bar-put" style="width:{p_pct:.1f}%"></div></div><div class="bar-label">{_fmt_dollar_no_sign(pg)}</div></div></td>
  <td class="{ng_class}">{_fmt_dollar(ng)}</td>
  <td>{pct:.1f}%</td>
</tr>""")

    return f"""\
<div class="strike-table-wrap">
<table class="strike-table">
<thead><tr>
  <th>Strike</th>
  <th>Call GEX</th>
  <th>Put GEX</th>
  <th>Net GEX</th>
  <th>%Abs</th>
</tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
</div>"""


def _build_gex_chart(strikes):
    if not strikes:
        return ""

    abs_max = max(max(abs(s["call_gex"]), abs(s["put_gex"])) for s in strikes) if strikes else 1
    if abs_max <= 0:
        abs_max = 1

    rows = []
    for s in strikes:
        stk = s["strike"]
        c_pct = abs(s["call_gex"]) / abs_max * 100
        p_pct = abs(s["put_gex"]) / abs_max * 100
        rows.append(f"""\
<div class="gex-chart-row">
  <div class="gex-chart-strike">${stk:.2f}</div>
  <div class="gex-chart-bar-wrapper">
    <div class="gex-chart-call" style="width:{c_pct:.1f}%"></div>
    <div class="gex-chart-put" style="width:{p_pct:.1f}%"></div>
  </div>
  <div class="gex-chart-label">{_fmt_dollar_no_sign(s["call_gex"])} / {_fmt_dollar_no_sign(s["put_gex"])}</div>
</div>""")

    return f"""\
<div class="gex-chart">
  <div class="section-title">GEX Profile by Strike <span style="font-weight:400;color:#64748b;font-size:13px;">(blue = Call GEX, red = Put GEX)</span></div>
  {chr(10).join(rows)}
  <div style="margin-top:8px;font-size:11px;color:#94a3b8;text-align:right;">Bar width proportional to absolute GEX contribution</div>
</div>"""


def _build_data_quality(dq):
    parts = [f"<strong>{dq['valid_options']}</strong> / {dq['total_options']} contracts valid"]
    if dq.get("skipped_no_gamma"):
        parts.append(f"{dq['skipped_no_gamma']} skipped (no gamma)")
    if dq.get("skipped_no_oi"):
        parts.append(f"{dq['skipped_no_oi']} skipped (no OI)")
    return f'<div class="data-quality">{" | ".join(parts)}</div>'


def _build_header(ticker, stock_price, expiration, dte, generated_at, is_multi=False):
    title = f"Gamma Exposure Analysis" + (f" &mdash; {escape(ticker)}" if ticker else "")
    subtitle_parts = []
    if stock_price is not None:
        subtitle_parts.append(f"Stock: ${stock_price:.2f}")
    if expiration:
        subtitle_parts.append(f"Exp: {escape(expiration)}" + (f" ({dte} DTE)" if dte else ""))
    subtitle_parts.append(f"Generated: {escape(generated_at)}")

    return f"""\
<div class="header">
  <h1>{title}</h1>
  <div class="subtitle">{" | ".join(f'<span>{p}</span>' for p in subtitle_parts)}</div>
</div>"""


def _build_metrics_section(metrics):
    cards = []
    cards.append(_build_metric_card("Net GEX", _fmt_dollar(metrics.get("net_gex")),
                                     "positive" if (metrics.get("net_gex") or 0) >= 0 else "negative",
                                     f"per 1%: {_fmt_dollar(metrics.get('net_gex_1pct'))}"))
    cards.append(_build_metric_card("Absolute GEX", _fmt_dollar_no_sign(metrics.get("abs_gex")), "info"))
    cards.append(_build_metric_card("Call GEX (total)", _fmt_dollar_no_sign(metrics.get("total_call_gex")), "positive"))
    cards.append(_build_metric_card("Put GEX (total)", _fmt_dollar_no_sign(metrics.get("total_put_gex")), "negative"))
    cards.append(_build_metric_card("Call Wall",
                                     f"${_fmt(metrics.get('call_wall_strike'), 'N/A'):.2f}" if metrics.get("call_wall_strike") is not None else "N/A",
                                     "info"))
    cards.append(_build_metric_card("Put Wall",
                                     f"${_fmt(metrics.get('put_wall_strike'), 'N/A'):.2f}" if metrics.get("put_wall_strike") is not None else "N/A",
                                     "info"))
    cards.append(_build_metric_card("Gamma Flip",
                                     f"${_fmt(metrics.get('gamma_flip'), 'N/A'):.2f}" if metrics.get("gamma_flip") is not None else "N/A",
                                     "neutral"))
    return f'<div class="card-grid">{"".join(cards)}</div>'


def _build_stock_price_context(metrics, stock_price):
    gamma_flip = metrics.get("gamma_flip")
    net_gex = metrics.get("net_gex")
    if gamma_flip is None or stock_price is None or net_gex is None:
        return ""

    if net_gex > 0 and stock_price > gamma_flip:
        note = f"Stock (${stock_price:.2f}) is above Gamma Flip (${gamma_flip:.2f}) &mdash; dealers are net stabilizing."
    elif net_gex < 0 and stock_price < gamma_flip:
        note = f"Stock (${stock_price:.2f}) is below Gamma Flip (${gamma_flip:.2f}) &mdash; dealers are net amplifying."
    else:
        note = f"Stock (${stock_price:.2f}) vs Gamma Flip (${gamma_flip:.2f}) &mdash; mixed signals."

    return f'<p style="font-size:13px;color:#64748b;margin-bottom:24px;">{note}</p>'


# =========================================================================
# Full HTML page
# =========================================================================

def build_html(data_list, titles=None):
    """Generate a complete HTML page from one or more GEX data dicts."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ticker = data_list[0].get("ticker", "")
    sections = []

    for i, data in enumerate(data_list):
        metrics = data.get("metrics", {})
        strikes = data.get("strikes", [])
        dq = data.get("data_quality", {})
        stock_price = data.get("stock_price")
        expiration = data.get("expiration")
        dte = data.get("dte")
        regime = data.get("regime", "N/A")
        generated_at = data.get("generated_at", now)

        label = titles[i] if titles and i < len(titles) else (f"{expiration} ({dte} DTE)" if expiration else f"Expiry {i + 1}")

        html = ""
        if len(data_list) > 1:
            html += f'<div class="section-title" style="margin-top:16px;">{escape(label)}</div>'

        html += _build_regime_banner(regime)
        html += _build_stock_price_context(metrics, stock_price)
        html += _build_metrics_section(metrics)
        html += _build_strike_table(strikes, metrics.get("abs_gex"))
        html += _build_gex_chart(strikes)
        html += _build_data_quality(dq)
        sections.append(html)

    # Build tabs for multi-expiry
    header = _build_header(ticker, data_list[0].get("stock_price"),
                           data_list[0].get("expiration") if len(data_list) == 1 else None,
                           data_list[0].get("dte") if len(data_list) == 1 else None,
                           now)

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GEX Analysis{f" - {ticker}" if ticker else ""}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
{header}
{chr(10).join(sections)}
<div class="footer">Gamma Exposure (GEX) calculated using SpotGamma methodology &mdash; GEX = Gamma &times; OI &times; 100 &times; S&sup2; &mdash; For educational purposes only</div>
</div>
</body>
</html>"""


# =========================================================================
# CLI
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate an HTML report from GEX JSON data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  C:\\Python314\\python.exe scripts\\gex_to_html.py "
            "--input output\\gex_avgo_30d.json\n"
            "  C:\\Python314\\python.exe scripts\\gex_to_html.py "
            "--input output\\gex_avgo_30d.json --output report.html\n"
            "  C:\\Python314\\python.exe scripts\\gex_to_html.py "
            "--input output\\gex_avgo_30d.json output\\gex_avgo_60d.json "
            "--output output\\gex_avgo.html\n"
        ),
    )
    parser.add_argument(
        "--input", "-i", type=str, nargs="+", required=True,
        help="One or more GEX JSON files to include in the report.",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output HTML file path.  Defaults to <input_stem>.html for "
        "single files, output/gex_combined.html for multiple.",
    )
    parser.add_argument(
        "--label", "-l", type=str, nargs="*", default=None,
        help="Labels for each input (e.g. --label '30 DTE' '60 DTE').",
    )
    args = parser.parse_args()

    data_list = []
    titles = []
    for fp in args.input:
        try:
            with open(fp) as f:
                data_list.append(json.load(f))
            p = Path(fp)
            # Derive a short label from the filename
            stem = p.stem.replace("gex_", "").replace("_", " ").title()
            titles.append(stem)
        except Exception as e:
            print(f"Error reading {fp}: {e}", file=sys.stderr)
            sys.exit(1)

    if not data_list:
        print("No data loaded.", file=sys.stderr)
        sys.exit(1)

    if args.label:
        if len(args.label) != len(data_list):
            print(f"Warning: got {len(args.label)} labels but {len(data_list)} inputs.  Ignoring labels.",
                  file=sys.stderr)
        else:
            titles = args.label

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    elif len(data_list) == 1:
        out_path = Path(args.input[0]).with_suffix(".html")
    else:
        out_path = Path("output") / "gex_combined.html"

    html = build_html(data_list, titles=titles)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    ticker = data_list[0].get("ticker", "")
    name = out_path.name
    count = len(data_list)
    label = "expiries" if count > 1 else "expiry"
    print(f"Generated {name} — {ticker} ({count} {label})")


if __name__ == "__main__":
    main()
