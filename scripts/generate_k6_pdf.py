import json
import sys

# optional reportlab
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

k6_json = sys.argv[1]
out_pdf = sys.argv[2]

with open(k6_json) as f:
    data = json.load(f)

if not HAS_REPORTLAB:
    print("ERROR: reportlab não instalado. Pulei a geração de PDF K6. Instale: pip install -r requirements.txt")
    sys.exit(0)

styles = getSampleStyleSheet()
doc = SimpleDocTemplate(out_pdf, pagesize=A4)
content = []

content.append(Paragraph("📊 Relatório K6 – TeaStore", styles["Heading1"]))
content.append(Spacer(1, 12))

content.append(Paragraph("<pre>" + json.dumps(data, indent=2) + "</pre>", styles["Normal"]))

doc.build(content)

print("PDF gerado:", out_pdf)
