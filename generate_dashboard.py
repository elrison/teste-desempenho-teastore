import argparse, json, os

# Optional heavy deps: try to import and fall back gracefully with helpful messages.
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

# optional pandas for JMeter CSV parsing
try:
    import pandas as pd
    HAS_PANDAS = True
except Exception:
    pd = None
    HAS_PANDAS = False

parser = argparse.ArgumentParser(description="Gerar dashboard consolidado")
parser.add_argument("--k6", required=True, help="Arquivo JSON do K6")
parser.add_argument("--jmeter", required=True, help="Arquivo .jtl do JMeter")
parser.add_argument("--locust", required=True, help="Relatório HTML do Locust")
parser.add_argument("--out", default="dashboard.html", help="Saída HTML")
parser.add_argument("--pdf", default="relatorio.pdf", help="Saída PDF")
args = parser.parse_args()

k6_data = {}
if os.path.exists(args.k6):
    with open(args.k6) as f:
        try:
            k6_data = json.load(f)
        except Exception:
            k6_data = {}

# JMeter summary (supports CSV produced by CI)
jmeter_summary = {}
if os.path.exists(args.jmeter) and pd is not None:
    try:
        df = pd.read_csv(args.jmeter)
        # normalize column names
        cols = [c.lower() for c in df.columns]
        df.columns = cols
        # basic metrics
        total = len(df)
        elapsed_col = 'elapsed' if 'elapsed' in df.columns else df.columns[0]
        avg_latency = float(df[elapsed_col].mean()) if total > 0 else None
        p50 = float(df[elapsed_col].quantile(0.5)) if total > 0 else None
        p95 = float(df[elapsed_col].quantile(0.95)) if total > 0 else None
        p99 = float(df[elapsed_col].quantile(0.99)) if total > 0 else None
        # success column
        success = None
        if 'success' in df.columns:
            success = df['success'].astype(str).map(lambda s: s.lower() in ('true','1','t','y'))
        error_rate = (1.0 - float(success.mean())) if success is not None and total>0 else None
        # throughput (req/s)
        throughput = None
        if 'timestamp' in df.columns:
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                throughput = float(df.resample('1s').size().mean())
            except Exception:
                throughput = None

        jmeter_summary = {
            'tool': 'jmeter',
            'requests': total,
            'avg_latency_ms': avg_latency,
            'p50_ms': p50,
            'p95_ms': p95,
            'p99_ms': p99,
            'error_rate': error_rate,
            'throughput_rps': throughput,
        }
    except Exception:
        jmeter_summary = {}
else:
    # cannot parse without pandas or file missing
    jmeter_summary = {}

# Locust: try parse locust CSV stats if present (locust --csv=locust-teastore/locust)
locust_summary = {}
locust_csv = os.path.join('locust-teastore', 'locust_stats.csv')
if os.path.exists(locust_csv) and pd is not None:
    try:
        ldf = pd.read_csv(locust_csv)
        # locust stats has a summary row 'Total' often; try to find it
        if 'Name' in ldf.columns:
            total_row = ldf[ldf['Name'].str.lower() == 'total']
            if not total_row.empty:
                total_row = total_row.iloc[0]
                locust_summary = {
                    'requests': int(total_row.get('Request Count', total_row.get('Requests', 0))),
                    'avg_latency_ms': float(total_row.get('Average Response Time', 0) or 0),
                    'min_ms': float(total_row.get('Min Response Time', 0) or 0),
                    'max_ms': float(total_row.get('Max Response Time', 0) or 0),
                    'error_rate': float(total_row.get('Failure Count', 0) or 0) / max(1, int(total_row.get('Request Count', total_row.get('Requests', 1) or 1)))
                }
    except Exception:
        locust_summary = {}

# merge into unified
unified = { 'k6': k6_data.get('metrics', {}), 'jmeter': jmeter_summary, 'locust': locust_summary }
with open('summary-unified.json', 'w') as uf:
    json.dump(unified, uf, indent=2)

html = f"""
<html>
<head><title>Dashboard Consolidado — TeaStore</title></head>
<body>
<h1>Dashboard Consolidado — TeaStore</h1>
<h2>Resumo K6</h2>
<pre>{json.dumps(k6_data.get("metrics", {}), indent=2)}</pre>

<h2>Resumo JMeter (unificado)</h2>
<pre>{json.dumps(jmeter_summary, indent=2)}</pre>

<h2>Resumo Unificado</h2>
<pre>{json.dumps({ 'k6_metrics': k6_data.get('metrics', {}), 'jmeter': jmeter_summary }, indent=2)}</pre>

<h2>Relatórios</h2>
<ul>
<li><a href="{args.jmeter}">JMeter Report</a></li>
<li><a href="{args.locust}">Locust Report</a></li>
</ul>
</body>
</html>
"""

with open(args.out, "w") as f:
    f.write(html)

# write unified summary JSON for downstream analysis
unified = { 'k6': k6_data.get('metrics', {}), 'jmeter': jmeter_summary }
with open('summary-unified.json', 'w') as uf:
    json.dump(unified, uf, indent=2)

# --- Gera PDF (opcional) ---
if not HAS_REPORTLAB:
    print("⚠️  reportlab não está instalado. Pulei a geração de PDF. Instale as dependências: pip install -r requirements.txt")
else:
    try:
        doc = SimpleDocTemplate(args.pdf, pagesize=A4)
        styles = getSampleStyleSheet()
        content = [
            Paragraph("Dashboard Consolidado — TeaStore", styles["Heading1"]),
            Spacer(1, 12),
            Paragraph("Relatório unificado com dados do K6, JMeter e Locust", styles["Normal"]),
            Spacer(1, 12),
            Paragraph(f"K6: {args.k6}", styles["Normal"]),
            Paragraph(f"JMeter: {args.jmeter}", styles["Normal"]),
            Paragraph(f"Locust: {args.locust}", styles["Normal"]),
        ]
        doc.build(content)
        print("✅ PDF gerado:", args.pdf)
    except Exception as e:
        print("Erro ao gerar PDF:", e)

print("✅ Dashboard gerado:", args.out)
