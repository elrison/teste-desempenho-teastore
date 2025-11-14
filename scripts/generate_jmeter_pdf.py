from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import sys

graphs_dir = sys.argv[1]
out_pdf = sys.argv[2]

styles = getSampleStyleSheet()
doc = SimpleDocTemplate(out_pdf, pagesize=A4)
content = []

content.append(Paragraph("📊 Relatório JMeter – TeaStore", styles["Heading1"]))
content.append(Spacer(1, 12))

for chart in ["response_time.png", "throughput.png", "error_rate.png"]:
    path = f"{graphs_dir}/{chart}"
    content.append(Image(path, width=500, height=300))
    content.append(Spacer(1, 24))

doc.build(content)
print("✅ PDF JMeter gerado:", out_pdf)
