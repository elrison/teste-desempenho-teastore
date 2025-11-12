import argparse, json, pandas as pd
from bs4 import BeautifulSoup
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

parser = argparse.ArgumentParser()
parser.add_argument("--k6", required=True)
parser.add_argument("--jmeter", required=True)
parser.add_argument("--locust", required=True)
parser.add_argument("--out", default="dashboard.html")
parser.add_argument("--pdf", default="report.pdf")
args = parser.parse_args()

def read_k6(path):
    with open(path) as f:
        data = json.load(f)
    http_req = data.get('metrics', {}).get('http_req_duration', {}).get('avg', 0)
    failed = data.get('metrics', {}).get('http_req_failed', {}).get('rate', 0)
    return {"Ferramenta": "K6", "Tempo Médio (ms)": round(http_req, 2), "Falhas (%)": round(failed * 100, 2)}

def read_jmeter(path):
    with open(path) as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    title = soup.find("title").text if soup.find("title") else "Relatório JMeter"
    return {"Ferramenta": "JMeter", "Tempo Médio (ms)": 0, "Falhas (%)": 0, "Resumo": title}

def read_locust(path):
    with open(path) as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    stats = soup.find_all("td")
    return {"Ferramenta": "Locust", "Tempo Médio (ms)": 0, "Falhas (%)": 0}

dados = [read_k6(args.k6), read_jmeter(args.jmeter), read_locust(args.locust)]
df = pd.DataFrame(dados)
html_table = df.to_html(index=False)

with open(args.out, "w") as f:
    f.write(f"<html><head><title>Dashboard Consolidado</title></head><body><h1>Resumo Consolidado</h1>{html_table}</body></html>")

styles = getSampleStyleSheet()
doc = SimpleDocTemplate(args.pdf)
story = [Paragraph("Relatório Consolidado de Performance", styles['Title']), Spacer(1, 12)]
for _, row in df.iterrows():
    story.append(Paragraph(f"{row['Ferramenta']}: {row.to_dict()}", styles['Normal']))
    story.append(Spacer(1, 12))
doc.build(story)
