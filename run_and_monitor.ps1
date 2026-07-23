powershell -NoProfile -File run_cov_config.ps1
Start-Sleep -Seconds 5
Start-Process python -ArgumentList 'monitor_cov.py' -NoNewWindow -PassThru
