#!/usr/bin/env python3
import json
from pathlib import Path
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

OUT = Path(".")
CHARTS = OUT / "charts"
CHARTS.mkdir(exist_ok=True)

def save_fig(fig, name):
    path = CHARTS / name
    fig.savefig(path, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return path

# Load k6
k6_path = Path("k6-complex.json")
k6_metrics = {}
if k6_path.exists():
    k6 = json.loads(k6_path.read_text(encoding='utf-8'))
    http_req = k6.get("metrics", {}).get("http_req_duration", {})
    k6_metrics = {
        "avg": http_req.get("values", {}).get("avg"),
        "p95": http_req.get("values", {}).get("p(95)"),
        "p99": http_req.get("values", {}).get("p(99)"),
        "checks": k6.get("metrics", {}).get("checks", {}).get("values", {})
    }

# Create chart for k6 avg
if k6_metrics.get("avg") is not None:
    fig, ax = plt.subplots(figsize=(6,3))
    ax.bar(['k6'], [k6_metrics['avg']])
    ax.set_title("k6 avg latency (ms)")
    ax.set_ylabel("ms")
    save_fig(fig, "k6_avg.png")

# Parse locust HTML (if exists)
locust_path = Path("complex.html")
locust_summary = {}
if locust_path.exists():
    soup = BeautifulSoup(locust_path.read_text(encoding='utf-8'), "html.parser")
    table = soup.find("table")
    if table:
        rows = [[td.get_text(strip=True) for td in tr.find_all(["td","th"])] for tr in table.find_all("tr")]
        if len(rows) > 1:
            locust_summary['table_header'] = rows[0]
            locust_summary['rows'] = rows[1:10]

# Parse jmeter index (simple attempt)
jmeter_path = Path("index.html")
jmeter_preview = None
if jmeter_path.exists():
    soup = BeautifulSoup(jmeter_path.read_text(encoding='utf-8'), "html.parser")
    table = soup.find(id="summaryTable") or soup.find("table")
    if table:
        rows = [[td.get_text(strip=True) for td in tr.find_all(["td","th"])] for tr in table.find_all("tr")]
        if len(rows) > 1:
            jmeter_preview = {"header": rows[0], "rows": rows[1:6]}

# Heatmap generation (simple)
tools = []
if k6_metrics:
    tools.append(("k6", k6_metrics.get("avg") or 0, k6_metrics.get("p95") or 0, k6_metrics.get("p99") or 0))
if jmeter_preview:
    avg = None
    # attempt to find numeric in jmeter preview
    try:
        header = jmeter_preview["header"]
        rows = jmeter_preview["rows"]
        avg_col_index = None
        for i, h in enumerate(header):
            if "Average" in h or "Avg" in h:
                avg_col_index = i
                break
        if avg_col_index is not None:
            vals = []
            for r in rows:
                try:
                    vals.append(float(r[avg_col_index]))
                except Exception:
                    pass
            if vals:
                avg = sum(vals) / len(vals)
    except Exception:
        avg = None
    tools.append(("jmeter", avg or 0, 0, 0))
if locust_summary:
    # try derive avg from Locust table if possible
    avg_loc = None
    try:
        header = locust_summary['table_header']
        rows = locust_summary['rows']
        # pick first numeric column heuristically
        for i, val in enumerate(rows[0]):
            try:
                float(val)
                avg_loc = float(val)
                break
            except Exception:
                continue
    except Exception:
        avg_loc = None
    tools.append(("locust", avg_loc or 0, 0, 0))

if tools:
    arr = np.array([[t[1], t[2], t[3]] for t in tools], dtype=float)
    fig, ax = plt.subplots(figsize=(6,3))
    im = ax.imshow(arr, aspect='auto')
    ax.set_yticks(np.arange(len(tools)))
    ax.set_yticklabels([t[0] for t in tools])
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(["avg","p95","p99"])
    fig.colorbar(im, ax=ax)
    save_fig(fig, "heatmap_tools.png")

# Build dashboard HTML
html = "<!doctype html><html><head><meta charset='utf-8'><title>Dashboard Consolidado</title></head><body>"
html += "<h1>Dashboard Consolidado — TeaStore</h1>"
if (CHARTS/"k6_avg.png").exists():
    html += "<h2>k6</h2><img src='charts/k6_avg.png' style='max-width:800px;'>"
if (CHARTS/"heatmap_tools.png").exists():
    html += "<h2>Heatmap</h2><img src='charts/heatmap_tools.png' style='max-width:800px;'>"
html += "<h2>Resumos extraídos</h2>"
html += f"<pre>k6_metrics = {json.dumps(k6_metrics, indent=2, ensure_ascii=False)}</pre>"
html += f"<pre>locust_preview = {json.dumps(locust_summary, indent=2, ensure_ascii=False)}</pre>"
html += f"<pre>jmeter_preview = {json.dumps(jmeter_preview, indent=2, ensure_ascii=False)}</pre>"
html += "<h3>Relatórios originais</h3><ul>"
if jmeter_path.exists(): html += "<li><a href='index.html'>JMeter report (index.html)</a></li>"
if locust_path.exists(): html += "<li><a href='complex.html'>Locust report (complex.html)</a></li>"
if k6_path.exists(): html += "<li><a href='k6-complex.json'>k6 summary (JSON)</a></li>"
html += "</ul></body></html>"

Path("dashboard.html").write_text(html, encoding='utf-8')

# Simple PDF
pdf_path = Path("report.pdf")
doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
styles = getSampleStyleSheet()
elems = [Paragraph("Relatório Consolidado — TeaStore", styles['Title']), Spacer(1,12)]
elems.append(Paragraph("k6 metrics:", styles['Heading2']))
elems.append(Paragraph(str(k6_metrics), styles['Normal']))
if (CHARTS/"k6_avg.png").exists():
    elems.append(Spacer(1,12))
    elems.append(RLImage(str(CHARTS/"k6_avg.png"), width=400, height=200))
if (CHARTS/"heatmap_tools.png").exists():
    elems.append(Spacer(1,12))
    elems.append(RLImage(str(CHARTS/"heatmap_tools.png"), width=400, height=200))
doc.build(elems)

print("Dashboard and PDF generated: dashboard.html, report.pdf, charts/*")
