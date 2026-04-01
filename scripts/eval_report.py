"""Generate HTML comparison report — Raw LLM vs CLARKE."""

from datetime import UTC, datetime
from pathlib import Path


def generate_comparison_report(summary, results, output_path: str) -> None:
    """Generate side-by-side comparison HTML report."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    s = summary

    # Token savings color
    savings_color = (
        "#28a745"
        if s.token_savings_pct > 50
        else "#ffc107"
        if s.token_savings_pct > 20
        else "#dc3545"
    )

    # Hallucination comparison
    halluc_raw_pct = s.raw_hallucination_rate * 100
    halluc_clarke_pct = s.clarke_hallucination_rate * 100

    # Per-question rows
    rows = ""
    for r in results:
        token_saved = r.raw_input_tokens - r.clarke_input_tokens
        halluc_class = (
            "pass" if r.clarke_hallucination_count <= r.raw_hallucination_count else "fail"
        )
        rows += f"""<tr>
<td>{r.question_id}</td>
<td title="{r.query}">{r.query[:50]}...</td>
<td>{r.category}</td>
<td class="metric">{r.raw_input_tokens:,}</td>
<td class="metric">{r.clarke_input_tokens:,}</td>
<td class="metric {"pass" if token_saved > 0 else "fail"}">{token_saved:+,}</td>
<td class="metric">{r.raw_latency_ms:,}ms</td>
<td class="metric">{r.clarke_latency_ms:,}ms</td>
<td class="metric">{r.raw_hallucination_count}</td>
<td class="metric {halluc_class}">{r.clarke_hallucination_count}</td>
<td class="metric">{r.raw_correctness:.2f}</td>
<td class="metric">{r.clarke_correctness:.2f}</td>
<td class="metric">{r.clarke_retrieved_count}</td>
</tr>"""

    html = f"""<!DOCTYPE html>
<html><head>
<title>CLARKE vs Raw LLM — Evaluation Report</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
h1 {{ color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }}
h2 {{ color: #16213e; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th, td {{ border: 1px solid #dee2e6; padding: 8px 12px; text-align: left; font-size: 0.9em; }}
th {{ background: #16213e; color: white; font-weight: 600; }}
tr:nth-child(even) {{ background: #f8f9fa; }}
.pass {{ color: #28a745; font-weight: bold; }}
.fail {{ color: #dc3545; font-weight: bold; }}
.metric {{ font-family: monospace; text-align: right; }}
.card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.big-number {{ font-size: 2.5em; font-weight: bold; margin: 5px 0; }}
.stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
.stat-card {{ background: white; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.stat-label {{ color: #6c757d; font-size: 0.85em; text-transform: uppercase; }}
.bar {{ height: 30px; border-radius: 4px; transition: width 0.5s; }}
.bar-container {{ background: #e9ecef; border-radius: 4px; overflow: hidden; margin: 5px 0; }}
svg {{ margin: 10px 0; }}
</style>
</head><body>
<h1>CLARKE vs Raw LLM — Evaluation Report</h1>
<p>Generated: {timestamp} | Questions: {s.total_questions} | Model: gpt-4o-mini</p>

<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-label">Token Savings</div>
    <div class="big-number" style="color: {savings_color}">{s.token_savings_pct:.1f}%</div>
    <div>{s.raw_total_input_tokens + s.raw_total_output_tokens:,} → {s.clarke_total_input_tokens + s.clarke_total_output_tokens:,}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Latency Delta</div>
    <div class="big-number" style="color: {"#28a745" if s.latency_delta_ms <= 0 else "#dc3545"}">{s.latency_delta_ms:+.0f}ms</div>
    <div>Mean: {s.raw_mean_latency_ms:.0f}ms → {s.clarke_mean_latency_ms:.0f}ms</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Hallucination Rate</div>
    <div class="big-number" style="color: {"#28a745" if halluc_clarke_pct <= halluc_raw_pct else "#dc3545"}">{halluc_clarke_pct:.0f}%</div>
    <div>Raw: {halluc_raw_pct:.0f}% → CLARKE: {halluc_clarke_pct:.0f}%</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Correctness Delta</div>
    <div class="big-number" style="color: {"#28a745" if s.correctness_delta >= 0 else "#dc3545"}">{s.correctness_delta:+.3f}</div>
    <div>Raw: {s.raw_mean_correctness:.3f} → CLARKE: {s.clarke_mean_correctness:.3f}</div>
  </div>
</div>

<h2>Summary Comparison</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Raw LLM</th><th>CLARKE</th><th>Winner</th></tr>
<tr><td>Total input tokens</td><td class="metric">{s.raw_total_input_tokens:,}</td><td class="metric">{s.clarke_total_input_tokens:,}</td><td class="{"pass" if s.clarke_total_input_tokens < s.raw_total_input_tokens else "fail"}">{"CLARKE" if s.clarke_total_input_tokens < s.raw_total_input_tokens else "Raw LLM"}</td></tr>
<tr><td>Total output tokens</td><td class="metric">{s.raw_total_output_tokens:,}</td><td class="metric">{s.clarke_total_output_tokens:,}</td><td class="metric">—</td></tr>
<tr><td>Mean latency</td><td class="metric">{s.raw_mean_latency_ms:,.0f}ms</td><td class="metric">{s.clarke_mean_latency_ms:,.0f}ms</td><td class="{"pass" if s.clarke_mean_latency_ms <= s.raw_mean_latency_ms else "fail"}">{"CLARKE" if s.clarke_mean_latency_ms <= s.raw_mean_latency_ms else "Raw LLM"}</td></tr>
<tr><td>p95 latency</td><td class="metric">{s.raw_p95_latency_ms:,.0f}ms</td><td class="metric">{s.clarke_p95_latency_ms:,.0f}ms</td><td class="{"pass" if s.clarke_p95_latency_ms <= s.raw_p95_latency_ms else "fail"}">{"CLARKE" if s.clarke_p95_latency_ms <= s.raw_p95_latency_ms else "Raw LLM"}</td></tr>
<tr><td>Hallucination rate</td><td class="metric">{halluc_raw_pct:.1f}%</td><td class="metric">{halluc_clarke_pct:.1f}%</td><td class="{"pass" if halluc_clarke_pct <= halluc_raw_pct else "fail"}">{"CLARKE" if halluc_clarke_pct <= halluc_raw_pct else "Raw LLM"}</td></tr>
<tr><td>Mean correctness</td><td class="metric">{s.raw_mean_correctness:.3f}</td><td class="metric">{s.clarke_mean_correctness:.3f}</td><td class="{"pass" if s.clarke_mean_correctness >= s.raw_mean_correctness else "fail"}">{"CLARKE" if s.clarke_mean_correctness >= s.raw_mean_correctness else "Raw LLM"}</td></tr>
<tr><td>Mean retrieved items</td><td class="metric">N/A (all docs)</td><td class="metric">{s.clarke_mean_retrieved:.1f}</td><td class="pass">CLARKE</td></tr>
</table>
</div>

<h2>Token Efficiency</h2>
<div class="card">
<p><strong>Raw LLM</strong> sends ~{s.raw_total_input_tokens // s.total_questions:,} input tokens per query (entire corpus).</p>
<p><strong>CLARKE</strong> sends ~{s.clarke_total_input_tokens // max(s.total_questions, 1):,} input tokens per query (selective retrieval).</p>
<div class="bar-container">
  <div class="bar" style="width: 100%; background: #dc3545;"></div>
</div>
<p style="font-size: 0.85em; color: #6c757d;">Raw LLM: {s.raw_total_input_tokens:,} total tokens</p>
<div class="bar-container">
  <div class="bar" style="width: {max(1, 100 - s.token_savings_pct)}%; background: #28a745;"></div>
</div>
<p style="font-size: 0.85em; color: #6c757d;">CLARKE: {s.clarke_total_input_tokens:,} total tokens ({s.token_savings_pct:.1f}% reduction)</p>
</div>

<h2>Per-Question Results</h2>
<div class="card" style="overflow-x: auto;">
<table>
<tr>
<th>ID</th><th>Query</th><th>Category</th>
<th>Raw Tokens</th><th>CLARKE Tokens</th><th>Saved</th>
<th>Raw Latency</th><th>CLARKE Latency</th>
<th>Raw Halluc</th><th>CLARKE Halluc</th>
<th>Raw Correct</th><th>CLARKE Correct</th>
<th>Retrieved</th>
</tr>
{rows}
</table>
</div>

<hr>
<p style="color: #6c757d; font-size: 0.9em;">Generated by CLARKE Evaluation Suite — Comparing brokered retrieval vs raw document stuffing</p>
</body></html>"""

    Path(output_path).write_text(html)
