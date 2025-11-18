# Collect container & compose debug info into a timestamped artifact folder
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\collect_docker_debug.ps1

$proj = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $proj

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$dir = Join-Path $proj "artifacts-debug-$timestamp"
New-Item -Path $dir -ItemType Directory -Force | Out-Null

Write-Host "Collecting docker-compose ps/listing..."
docker-compose ps -a > "$dir\compose-ps.txt" 2>&1

docker ps -a --filter name=teastore -a > "$dir\docker-ps-teastore.txt" 2>&1

Write-Host "Collecting logs for teastore-persistence and teastore-db (last 2000 lines)..."
docker-compose logs --no-log-prefix --tail 2000 teastore-persistence > "$dir\teastore-persistence-logs.txt" 2>&1
docker-compose logs --no-log-prefix --tail 2000 teastore-db > "$dir\teastore-db-logs.txt" 2>&1

# Try to find container IDs by name
$containers = docker ps -a --format "{{.ID}} {{.Names}}" | Select-String "teastore-persistence|teastore-db" -AllMatches
if ($containers) {
    $containers.Matches | ForEach-Object {
        $line = $_.Value.Trim()
        $parts = $line -split "\s+"
        $id = $parts[0]
        $name = $parts[1]
        Write-Host "Inspecting container $name ($id)"
        docker inspect $id > "$dir\inspect-$name.txt" 2>&1
        docker logs $id > "$dir\dockerlogs-$name.txt" 2>&1
    }
} else {
    Write-Host "No teastore containers found in 'docker ps -a' output"
}

Write-Host "Saved debug artifacts to: $dir"

# Also copy any existing artifact folders created by the reset script for correlation
Get-ChildItem -Path $proj -Filter "artifacts-full-*" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Done. Please attach the folder: $dir"
