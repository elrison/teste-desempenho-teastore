import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import sys

k6_json = sys.argv[1]
out_pdf = sys.argv[2]

styles = getSampleStyleSheet()
doc = SimpleDocTemplate(out_pdf, pagesize=A4)
content = []

with open(k6_json) as f:
    data = json.load(f)

content.append(Paragraph("📊 Relatório K6 – TeaStore", styles["Heading1"]))
content.append(Spacer(1, 12))

content.append(Paragraph("<pre>" + json.dumps(data, indent=2) + "</pre>", styles["Normal"]))

doc.build(content)

print("PDF gerado:", out_pdf)
