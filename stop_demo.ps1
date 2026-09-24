# =====================================================================
# AIS-42 HealthOutreach — stop both demo servers
# =====================================================================
Get-NetTCPConnection -LocalPort 5000, 8501 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Write-Host "Demo servers stopped." -ForegroundColor Green
