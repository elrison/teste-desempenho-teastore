import csv
import os
from collections import defaultdict

# Endpoints que devem aparecer no relatório
ENDPOINTS = [
    'GET Home',
    'GET Login Page',
    'POST Login Action',
    'GET Categoria',
    'GET Produto',
    'POST Logout'
]

CSV_PATH = os.path.join('jmeter-teastore', 'results-complexos.csv')
HTML_PATH = os.path.join('jmeter-teastore', 'report-complexos', 'index.html')

def parse_jmeter_csv(csv_path):
    summary = defaultdict(lambda: {'count': 0, 'fail': 0, 'apdex': 1.0})
    total = 0
    fail_total = 0
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row.get('label')
            success = row.get('success') == 'true'
            if label in ENDPOINTS:
                summary[label]['count'] += 1
                if not success:
                    summary[label]['fail'] += 1
                    fail_total += 1
                total += 1
    return summary, total, fail_total

def render_html(summary, total, fail_total):
    html = '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Relatório JMeter Customizado</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; }
        table { border-collapse: collapse; width: 60%; margin-bottom: 2em; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background: #f0f0f0; }
        .pie { width: 300px; height: 300px; }
    </style>
</head>
<body>
    <h2>APDEX (Application Performance Index)</h2>
    <table>
        <tr><th>Label</th><th>Requests</th><th>Fails</th><th>APDEX</th></tr>
'''
    for label in ENDPOINTS:
        data = summary.get(label, {'count': 0, 'fail': 0, 'apdex': 1.0})
        count = data['count']
        fail = data['fail']
        apdex = round((count - fail) / count, 3) if count else 1.0
        html += f'<tr><td>{label}</td><td>{count}</td><td>{fail}</td><td>{apdex}</td></tr>'
    html += '</table>'
    pass_pct = round(100 * (total - fail_total) / total, 2) if total else 100.0
    fail_pct = round(100 * fail_total / total, 2) if total else 0.0
    html += f'''
    <h2>Requests Summary</h2>
    <svg class="pie" viewBox="0 0 32 32">
      <circle r="16" cx="16" cy="16" fill="#b6e388" />
      <path d="M16 16 L16 0 A16 16 0 {1 if fail_pct > 50 else 0} 1 {16 + 16 * (1 - fail_pct/100):.2f} {16 + 16 * (fail_pct/100):.2f} Z" fill="#ff6f6f" />
    </svg>
    <p><span style="color:#ff6f6f">FAIL</span>: {fail_pct}% &nbsp; <span style="color:#b6e388">PASS</span>: {pass_pct}%</p>
    <hr>
    <p>Relatório gerado automaticamente. Apenas endpoints solicitados são exibidos.</p>
</body>
</html>'''
    return html

def main():
    summary, total, fail_total = parse_jmeter_csv(CSV_PATH)
    html = render_html(summary, total, fail_total)
    os.makedirs(os.path.dirname(HTML_PATH), exist_ok=True)
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Relatório gerado em: {HTML_PATH}')

if __name__ == '__main__':
    main()
