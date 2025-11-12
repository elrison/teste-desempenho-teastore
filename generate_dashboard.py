#!/usr/bin/env python3
import argparse, json, re, os
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

# =========================================
# PARÂMETROS CLI
# =========================================
parser = argparse.ArgumentParser(description="Gera dashboard consolidado de performance.")
parser.add_argument("--k6", required=True, help="Arquivo JSON do K6")
parser.add_argument("--jmeter", required=True, help="Arquivo HTML do JMeter (index.html)")
parser.add_argument("--locust", required=True, help="Arquivo HTML do Locust (complex.html)")
parser.add_argument("--out", default="dashboard.html", help="Arquivo HTML de saída")
parser.add_argument("--pdf", default="relatorio.pdf", help="Arquivo PDF consolidado")
args = parser.parse_args()

# =========================================
# FUNÇÕES DE EXTRAÇÃO
# =========================================
def extract_k6_metrics(file_path):
    if not os.path.exists(file_path):
        print(f"[WARN] K6 file not found: {file_path}")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metrics = data.get("metrics", {})
    http_req_duration = metrics.get("http_req_duration", {})
    avg = http_req_duration.get("avg")
    p90 = http_req_duration.get("p(90)")
    p95 = http_req_duration.get("p(95)")
    checks = metrics.get("checks", {}).get("value")
    vus = metrics.get("vus_max", {}).get("value", 0)
    print(f"[INFO] K6 metrics loaded: avg={avg}, p90={p90}, p95={p95}, checks={checks}")
    return {"avg": avg, "p90": p90, "p95": p95, "checks": checks, "vus": vus}


def extract_locust_stats(file_path):
    if not os.path.exists(file_path):
        print(f"[WARN] Locust report not found: {file_path}")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.text if soup.title else "Locust Report"
    summary_table = soup.find("table")
    text_snippet = soup.get_text()[:800]
    print(f"[INFO] Locust report loaded: {title}")
    return {"title": title, "snippet": text_snippet}


def extract_jmeter_summary(file_path):
    if not os.path.exists(file_path):
        print(f"[WARN] JMeter report not found: {file_path}")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    summary = soup.find("div", {"id": "statistics"})
    text_snippet = soup.get_text()[:800]
    print(f"[INFO] JMeter summary extracted.")
    return {"summary": summary, "snippet": text_snippet}

# =========================================
# EXTRAÇÃO
# =========================================
k6_data = extract_k6_metrics(args.k6)
locust_data = extract_locust_stats(args.locust)
jmeter_data = extract_jmeter_summary(args.jmeter)

# =========================================
# DASHBOARD HTML
# =========================================
html_content = f"""
<html>
<head>
  <meta charset="utf-8">
  <title>Dashboard Consolidado — TeaStore</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f4f4f9; }}
    h1 {{ color: #2b2b2b; }}
    h2 {{ color: #444; border-bottom: 2px solid #ccc; padding-bottom: 4px; }}
    pre {{ background: #fff; padding: 10px; border-radius: 8px; overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #ddd; }}
    .ok {{ color: green; font-weight: bold; }}
    .fail {{ color: red; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>📊 Dashboard Consolidado — TeaStore</h1>

  <h2>Resumo K6</h2>
  <table>
    <tr><th>Métrica</th><th>Valor</th></tr>
    <tr><td>Tempo médio (avg)</td><td>{k6_data['avg'] if k6_data else 'N/A'}</td></tr>
    <tr><td>p90</td><td>{k6_data['p90'] if k6_data else 'N/A'}</td></tr>
    <tr><td>p95</td><td>{k6_data['p95'] if k6_data else 'N/A'}</td></tr>
    <tr><td>Taxa de sucesso</td><td>{round(k6_data['checks']*100,2) if k6_data and k6_data['checks'] else 'N/A'}%</td></tr>
    <tr><td>VUs</td><td>{k6_data['vus'] if k6_data else 'N/A'}</td></tr>
  </table>

  <h2>Resumo Locust</h2>
  <pre>{locust_data['snippet'] if locust_data else 'Locust data not found.'}</pre>

  <h2>Resumo JMeter</h2>
  <pre>{jmeter_data['snippet'] if jmeter_data else 'JMeter data not found.'}</pre>

  <h2>Gráficos comparativos</h2>
  <img src="grafico_comparativo.png" width="600" />

</body>
</html>
"""

# =========================================
# GERA HTML
# =========================================
with open(args.out, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"[OK] Dashboard HTML gerado: {args.out}")

# =========================================
# GERA GRÁFICO
# =========================================
if k6_data:
    plt.figure(figsize=(6, 4))
    plt.bar(["avg", "p90", "p95"], [k6_data.get("avg", 0), k6_data.get("p90", 0), k6_data.get("p95", 0)], color=['#5DADE2', '#58D68D', '#F5B041'])
    plt.title("Métricas K6 — Duração das Requisições")
    plt.ylabel("ms")
    plt.savefig("grafico_comparativo.png")
    plt.close()

# =========================================
# GERA PDF
# =========================================
doc = SimpleDocTemplate(args.pdf, pagesize=A4)
styles = getSampleStyleSheet()
elements = []

elements.append(Paragraph("Dashboard Consolidado — TeaStore", styles["Title"]))
elements.append(Spacer(1, 12))

elements.append(Paragraph("<b>K6 Métricas</b>", styles["Heading2"]))
if k6_data:
    data_k6 = [["Métrica", "Valor"],
               ["avg", k6_data["avg"]],
               ["p90", k6_data["p90"]],
               ["p95", k6_data["p95"]],
               ["checks", k6_data["checks"]],
               ["vus", k6_data["vus"]]]
    t = Table(data_k6)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                           ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("BOX", (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(t)

elements.append(Spacer(1, 12))
elements.append(Paragraph("<b>Locust Trecho</b>", styles["Heading2"]))
elements.append(Paragraph(locust_data["snippet"][:500] if locust_data else "N/A", styles["Normal"]))

elements.append(Spacer(1, 12))
elements.append(Paragraph("<b>JMeter Trecho</b>", styles["Heading2"]))
elements.append(Paragraph(jmeter_data["snippet"][:500] if jmeter_data else "N/A", styles["Normal"]))

if os.path.exists("grafico_comparativo.png"):
    elements.append(Spacer(1, 12))
    elements.append(RLImage("grafico_comparativo.png", width=400, height=250))

doc.build(elements)
print(f"[OK] Relatório PDF gerado: {args.pdf}")
