from bs4 import BeautifulSoup
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import sys

html_file = sys.argv[1]
out_pdf = sys.argv[2]

with open(html_file) as f:
    soup = BeautifulSoup(f, "html.parser")

stats = soup.find("table")

doc = SimpleDocTemplate(out_pdf, pagesize=A4)
styles = getSampleStyleSheet()
content = []

content.append(Paragraph("📊 Relatório Locust – TeaStore", styles["Heading1"]))
content.append(Spacer(1, 12))

content.append(Paragraph(str(stats), styles["Normal"]))

doc.build(content)
print("PDF Locust gerado:", out_pdf)
