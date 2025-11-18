# Script para automatizar:
# 1) reiniciar teastore-persistence
# 2) aguardar a geração inicial de dados
# 3) executar um k6 curto
# 4) coletar logs e artefatos em uma pasta timestamped

Param()

$proj = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $proj

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$artifactDir = Join-Path $proj "artifacts-$timestamp"
New-Item -Path $artifactDir -ItemType Directory -Force | Out-Null

Write-Host "[1/4] Reiniciando teastore-persistence..."
docker-compose up -d --force-recreate teastore-persistence

# Poll logs for success message
Write-Host "[2/4] Aguardando geração inicial de dados (timeout ~6 minutos) ..."
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
    Write-Host "Logs salvos em: $artifactDir\teastore-persistence-full.txt"
    Exit 1
}

Write-Host "[OK] Geração inicial detectada. Salvando logs finais e seguindo para k6."
docker-compose logs --tail 1000 teastore-persistence > "$artifactDir\teastore-persistence-final.txt"

# Run k6
Write-Host "[3/4] Executando k6 (curto)..."
$k6Output = Join-Path $artifactDir 'k6_run_output.txt'
# Ensure debug dir exists
$k6DebugDir = Join-Path $proj 'k6-debug'
New-Item -Path $k6DebugDir -ItemType Directory -Force | Out-Null

# Run k6 and capture stdout/stderr
try {
    & k6 run --vus 2 --duration 30s --env HOST=http://localhost --env PORT=8080 "./k6-teastore/cenarios-complexos.js" 2>&1 | Tee-Object -FilePath $k6Output
} catch {
    Write-Host "[WARNING] Falha ao executar k6. Certifique-se de que o k6 está instalado e no PATH. Erro: $_"
}

# Collect debug HTML files (if the script wrote them)
Write-Host "[4/4] Coletando arquivos debug (debug_*.html) e logs..."
Get-ChildItem -Path $proj -Filter "debug_*.html" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $k6DebugDir -Force
}

# Save list of debug files
Get-ChildItem -Path $k6DebugDir -File | Select-Object Name, Length | Out-File "$artifactDir\k6_debug_files.txt"

# Save teastore-persistence tail (already saved) and env
docker-compose exec teastore-persistence printenv > "$artifactDir\teastore-persistence-env.txt" 2>$null

Write-Host "Concluído. Artefatos e logs em: $artifactDir"
Write-Host "Pasta com possíveis debug_*.html: $k6DebugDir"
Exit 0
