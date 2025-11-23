import json
import re
from pathlib import Path

base_path = Path('C:/Users/Elris/Music/testes-validos/locust-repo')

for vus in [100, 500, 1000]:
    html_file = base_path / f'report-{vus}-vus.html'
    
    print(f'\n=== LOCUST {vus} VUs ===')
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Procurar pelo objeto JavaScript com os dados
    match = re.search(r'const V=(\{.*?\});', html, re.DOTALL)
    
    if match:
        try:
            data = json.loads(match.group(1))
            
            # Pegar a última linha (Total)
            total_stats = data['requestsStatistics'][-1]
            
            print(f'Avg Response Time: {total_stats["avgResponseTime"]:.0f} ms')
            print(f'Min Response Time: {total_stats["minResponseTime"]:.0f} ms')
            print(f'Max Response Time: {total_stats["maxResponseTime"]:.0f} ms')
            print(f'Total RPS: {total_stats["totalRps"]:.2f}')
            print(f'Total Failures/s: {total_stats["totalFailPerSec"]:.2f}')
            print(f'Num Requests: {total_stats["numRequests"]}')
            print(f'Num Failures: {total_stats["numFailures"]}')
            
            # Tentar encontrar percentis no responseTimeStatistics
            if 'responseTimeStatistics' in data:
                print('\nPercentis:')
                for stat in data['responseTimeStatistics']:
                    if stat['name'] == 'Aggregated':
                        for key, value in stat.items():
                            if 'percentile' in key.lower():
                                print(f'{key}: {value} ms')
        except Exception as e:
            print(f'Erro ao processar: {e}')
    else:
        print('Não foi possível extrair os dados')
