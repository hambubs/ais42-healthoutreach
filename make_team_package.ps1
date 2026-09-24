# Build the shareable team package (docs + deck + code, no heavy data)
$root = $PSScriptRoot
$stage = Join-Path $env:TEMP "ais42_stage"
$zip = Join-Path $root "AIS-42_team_package.zip"

Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $zip -Force -ErrorAction SilentlyContinue

robocopy $root $stage /E /XD .venv .git __pycache__ raw /XF app.db *.tif *.pyc | Out-Null

Compress-Archive -Path "$stage\*" -DestinationPath $zip -Force
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue

$size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Team package ready: $zip ($size MB)" -ForegroundColor Green
Write-Host "Upload it to the team Google Drive folder."
