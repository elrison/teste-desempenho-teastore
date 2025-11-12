#!/usr/bin/env python3
# generate_dashboard.py
import json, os, sys, math
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

ROOT = Path('.')
charts_dir = ROOT / "charts"
charts_dir.mkdir(exist_ok=True)

# Helper: safe load JSON
def load_json_safe(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

# 1) Parse k6 summary JSON (k6-complex.json)
k6_path = ROOT / "k6-complex.json"
k6_summary = load_json_safe(k6_path) if k6_path.exists() else None

k6_metrics = {"avg": None, "p90": None, "p95": None, "p99": None, "checks": {}}
if k6_summary:
    # k6 summary has metrics at top-level 'metrics'
    metrics = k6_summary.get('metrics', {}) if isinstance(k6_summary, dict) else {}
    h = metrics.get('http_req_duration') or metrics.get('http_req_duration{expected_response:true}') or metrics.get('http_req_duration')
    if h and isinstance(h, dict):
        k6_metrics["avg"] = h.get('avg')
        # p(90) p(95) may be named 'p(90)' etc
        for pkey in ['p(90)', 'p(95)', 'p(99)']:
            val = h.get(pkey)
            if val is not None:
                if '90' in pkey: k6_metrics['p90'] = val
                if '95' in pkey: k6_metrics['p95'] = val
                if '99' in pkey: k6_metrics['p99'] = val
    # checks
    checks = {}
    for name, m in metrics.items():
        if name.startswith("checks"):
            checks[name] = m.get('rate') if isinstance(m, dict) else None
    k6_metrics['checks'] = checks

# 2) Parse Locust HTML summary (if exists)
locust_path = ROOT / "locust-teastore" / "complex.html"
locust_preview = {}
if locust_path.exists():
    soup = BeautifulSoup(locust_path.read_text(encoding='utf-8'), 'html.parser')
    # try to capture some tables/summary text
    title = soup.find('h1')
    locust_preview['title'] = title.text.strip() if title else 'Locust report'
    # find first table of stats
    table = soup.find('table')
    if table:
        # extract header and first data row
        headers = [th.text.strip() for th in table.find_all('th')]
        rows = table.find_all('tr')
        if len(rows) > 1:
            first = [td.text.strip() for td in rows[1].find_all('td')]
            locust_preview['table_first_row'] = dict(zip(headers[:len(first)], first))

# 3) JMeter report: try to read report index
jmeter_index = ROOT / "jmeter-teastore" / "report-complexos" / "index.html"
jmeter_preview = None
if jmeter_index.exists():
    jmeter_preview = str(jmeter_index)

# 4) Create a small comparative chart (if we have some numeric metrics)
# prepare a dataframe for chart: try to get avg from k6 and any locust/jmeter rough metrics
vals = {}
if k6_metrics.get('avg') is not None:
    vals['k6_avg_ms'] = k6_metrics['avg']
# try locate median from locust table
if locust_preview.get('table_first_row'):
    row = locust_preview['table_first_row']
    # typical Locust report uses 'Avg' column
    if 'Avg' in row:
        try:
            vals['locust_avg_ms'] = float(row['Avg'])
        except:
            pass

# simple bar chart comparison
if vals:
    df = pd.DataFrame(list(vals.items()), columns=['metric','value'])
    plt.figure(figsize=(6,3))
    plt.bar(df['metric'], df['value'])
    plt.title('Comparação Avg response (ms)')
    plt.ylabel('ms')
    plt.tight_layout()
    chart_file = charts_dir / "compare_avg.png"
    plt.savefig(chart_file)
    plt.close()
else:
    chart_file = None

# 5) Generate a heatmap placeholder: For heatmap we can use k6 percentiles (p90/p95/p99)
heatmap_file = charts_dir / "heatmap_tools.png"
if k6_metrics.get('p90') or k6_metrics.get('p95') or k6_metrics.get('p99'):
    percentiles = []
    labels = []
    for k in ('p90','p95','p99'):
        v = k6_metrics.get(k)
        if v:
            percentiles.append(v)
            labels.append(k)
    plt.figure(figsize=(4,3))
    plt.imshow([percentiles], aspect='auto')
    plt.yticks([])
    plt.xticks(range(len(labels)), labels)
    plt.colorbar()
    plt.title('Heatmap (k6 percentiles)')
    plt.tight_layout()
    plt.savefig(heatmap_file)
    plt.close()
else:
    # generate placeholder image
    import matplotlib.pyplot as plt
    plt.figure(figsize=(4,3))
    plt.text(0.5, 0.5, "Heatmap não disponível (sem percentis)", ha='center', va='center')
    plt.axis('off')
    plt.savefig(heatmap_file)
    plt.close()

# 6) Produce dashboard.html (simple)
html = f"""<!doctype html>
<html>
<head><meta charset='utf-8'><title>Dashboard Consolidado — TeaStore</title></head>
<body>
  <h1>Dashboard Consolidado — TeaStore</h1>
  <h2>Heatmap</h2>
  <img src='charts/{heatmap_file.name}' style='max-width:800px;'>
  <h2>Comparativo</h2>
  {"<img src='charts/compare_avg.png' style='max-width:800px;'>" if chart_file else "<p>Comparativo não disponível</p>"}
  <h2>Resumos extraídos</h2>
  <pre>k6_metrics = {json.dumps(k6_metrics, indent=2)}</pre>
  <pre>locust_preview = {json.dumps(locust_preview, indent=2)}</pre>
  <pre>jmeter_preview = {"'"+str(jmeter_preview)+"'" if jmeter_preview else "null"}</pre>
  <h3>Relatórios originais</h3>
  <ul>
    {"<li><a href='k6-complex.json'>k6 summary (JSON)</a></li>" if k6_path.exists() else ""}
    {"<li><a href='locust-teastore/complex.html'>locust complex (HTML)</a></li>" if locust_path.exists() else ""}
    {"<li><a href='jmeter-teastore/report-complexos/index.html'>JMeter report</a></li>" if jmeter_index.exists() else ""}
  </ul>
</body>
</html>
"""
with open(ROOT / "dashboard.html", "w", encoding='utf-8') as f:
    f.write(html)

# 7) Create PDF summary (simple)
doc = SimpleDocTemplate(str(ROOT / "relatorio_completo.pdf"), pagesize=A4)
styles = getSampleStyleSheet()
elems = []
elems.append(Paragraph("Relatório Consolidado — TeaStore", styles['Title']))
elems.append(Spacer(1, 12))
elems.append(Paragraph("Sumário K6", styles['Heading2']))
elems.append(Paragraph(json.dumps(k6_metrics, indent=2), styles['Code']))
elems.append(Spacer(1,12))
if chart_file:
    elems.append(Paragraph("Comparativo (avg)", styles['Heading2']))
    elems.append(RLImage(str(chart_file), width=400, height=200))
    elems.append(Spacer(1,12))
elems.append(Paragraph("Heatmap", styles['Heading2']))
elems.append(RLImage(str(heatmap_file), width=400, height=120))
elems.append(Spacer(1,12))
if locust_path.exists():
    elems.append(Paragraph("Locust summary (preview)", styles['Heading2']))
    elems.append(Paragraph(str(locust_preview.get('table_first_row', {})), styles['Code']))
if jmeter_index.exists():
    elems.append(Paragraph("JMeter report", styles['Heading2']))
    elems.append(Paragraph(f"Relatório HTML: {jmeter_index}", styles['Normal']))

doc.build(elems)
print("Dashboard gerado: dashboard.html, relatorio_completo.pdf, charts/*")
