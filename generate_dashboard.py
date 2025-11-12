import argparse, json, os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

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

html = f"""
<html>
<head><title>Dashboard Consolidado — TeaStore</title></head>
<body>
<h1>Dashboard Consolidado — TeaStore</h1>
<h2>Resumo K6</h2>
<pre>{json.dumps(k6_data.get("metrics", {}), indent=2)}</pre>

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

# --- Gera PDF ---
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

print("✅ Dashboard gerado:", args.out)
print("✅ PDF gerado:", args.pdf)
