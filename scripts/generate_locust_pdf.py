import sys
import os
from bs4 import BeautifulSoup

# optional reportlab
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

html_file = sys.argv[1]
out_pdf = sys.argv[2]

with open(html_file) as f:
    soup = BeautifulSoup(f, "html.parser")

stats = soup.find("table")

if not HAS_REPORTLAB:
    print("ERROR: reportlab não instalado. Pulei a geração de PDF Locust. Instale as dependências: pip install -r requirements.txt")
    sys.exit(0)

doc = SimpleDocTemplate(out_pdf, pagesize=A4)
styles = getSampleStyleSheet()
content = []

content.append(Paragraph("📊 Relatório Locust – TeaStore", styles["Heading1"]))
content.append(Spacer(1, 12))

content.append(Paragraph(str(stats), styles["Normal"]))

doc.build(content)
print("PDF Locust gerado:", out_pdf)
