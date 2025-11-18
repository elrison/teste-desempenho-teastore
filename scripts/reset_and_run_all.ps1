# Reset environment, start stack, wait for persistence, run k6/locust/jmeter via Docker
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\reset_and_run_all.ps1

$proj = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $proj

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$artifactDir = Join-Path $proj "artifacts-full-$timestamp"
New-Item -Path $artifactDir -ItemType Directory -Force | Out-Null

Write-Host "[1/5] Bringing down any existing stack and removing volumes..."
docker-compose down -v

Write-Host "[2/6] Starting stack WITH temporary root override (this may take a minute)..."
# Start with the root override so initial-data generation can run even if app user isn't present yet.
docker-compose -f docker-compose.yml -f ..\docker-compose.override.root.yml up -d --build

Write-Host "[3/5] Waiting for persistence to finish initial data generation (timeout ~6 min)..."
$success = $false
$maxIterations = 120
for ($i = 0; $i -lt $maxIterations; $i++) {
    docker-compose logs --tail 400 teastore-persistence > "$artifactDir\teastore-persistence-tail.txt"
    if (Select-String -Path "$artifactDir\teastore-persistence-tail.txt" -Pattern 'Initial data generation complete|Initial data generated|Generation finished|Done generating initial data' -Quiet) {
        $success = $true
        break
    }
    Start-Sleep -Seconds 3
    Write-Host "  aguardando... tentativa $($i+1)/$maxIterations"
}

if (-not $success) {
    Write-Host "[ERROR] Geração inicial NÃO detectada dentro do timeout. Salvando logs e saindo com erro."
    docker-compose logs --tail 1000 teastore-persistence > "$artifactDir\teastore-persistence-full.txt"
    docker-compose logs --tail 1000 teastore-db > "$artifactDir\teastore-db-full.txt"
    Write-Host "Logs salvos em: $artifactDir"
    Exit 1
}

Write-Host "[OK] Geração inicial detectada com override ROOT. Salvando logs intermediários e reiniciando stack sem override..."
docker-compose -f docker-compose.yml -f ..\docker-compose.override.root.yml logs --tail 1000 teastore-persistence > "$artifactDir\teastore-persistence-initial-with-root.txt"
docker-compose -f docker-compose.yml -f ..\docker-compose.override.root.yml logs --tail 1000 teastore-db > "$artifactDir\teastore-db-initial-with-root.txt"

# Now bring the stack down and bring it up normally (no root override) so services run with the proper app user
Write-Host "[4/6] Bringing down stack to remove root override and restart with normal config..."
docker-compose -f docker-compose.yml -f ..\docker-compose.override.root.yml down
Start-Sleep -Seconds 3

Write-Host "[5/6] Starting stack with normal configuration..."
docker-compose up -d --build

Write-Host "[OK] Stack restarted normally. Salvando logs finais."
docker-compose logs --tail 1000 teastore-persistence > "$artifactDir\teastore-persistence-final.txt"
docker-compose logs --tail 1000 teastore-db > "$artifactDir\teastore-db-final.txt"

# Run k6 in the compose network so it can reach the webui service
Write-Host "[4/5] Running k6 (containerized)..."
$k6Out = Join-Path $artifactDir 'k6_run_output.txt'
docker run --rm --network teastore-network -v ${PWD}:/scripts -w /scripts -e HOST=http://teastore-webui -e PORT=8080 loadimpact/k6 run k6-teastore/cenarios-complexos.js 2>&1 | Tee-Object -FilePath $k6Out

# Run Locust headless
Write-Host "[5/5] Running Locust (containerized, headless)..."
$locustOut = Join-Path $artifactDir 'locust_run_output.txt'
docker run --rm --network teastore-network -v ${PWD}/locust-teastore:/locust -w /locust loki/locust -f cenarios-complexos-locust.py --headless -u 10 -r 2 -t 30s --host=http://teastore-webui:8080 2>&1 | Tee-Object -FilePath $locustOut

# Run JMeter non-GUI if the script exists
$jmeterScript = Join-Path $proj 'jmeter-teastore/teste-carga-simples.jmx'
if (Test-Path $jmeterScript) {
    Write-Host "[optional] Running JMeter (containerized)"
    $jmeterOut = Join-Path $artifactDir 'jmeter_run_output.txt'
    docker run --rm --network teastore-network -v ${PWD}/jmeter-teastore:/jmeter -w /jmeter justb4/jmeter:5.4.1 -n -t teste-carga-simples.jmx -l results.jtl 2>&1 | Tee-Object -FilePath $jmeterOut
    Copy-Item -Path "$proj\jmeter-teastore\results.jtl" -Destination $artifactDir -Force -ErrorAction SilentlyContinue
}

# Collect debug html files (k6 script writes them to repo root by default)
Get-ChildItem -Path $proj -Filter "debug_*.html" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $artifactDir -Force
}

# Save list of files and finish
Get-ChildItem -Path $artifactDir -File | Select-Object Name, Length | Out-File "$artifactDir\artifacts_list.txt"
Write-Host "Concluído. Artefatos em: $artifactDir"
Exit 0
