$procId = Get-Content cov_proc.csv | Select-Object -Skip 1 | ForEach-Object { ($_ -split ',')[0].Trim('"') } | Select-Object -First 1

while (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 10
    @{
        pid = $procId
        status = 'RUNNING'
        checked_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    } | ConvertTo-Json | Set-Content cov_status.json
}

@{
    pid = $procId
    status = 'DONE'
    checked_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
} | ConvertTo-Json | Set-Content cov_status.json

# Generate coverage reports from accumulated .coverage data
$env:PYTHONIOENCODING = 'utf-8'
Start-Process -FilePath python -ArgumentList '-m', 'coverage', 'json', '-o', 'coverage.json' -WorkingDirectory 'C:\AIOps_Agent_bak' -Wait -NoNewWindow
Start-Process -FilePath python -ArgumentList 'cov_summary.py' -WorkingDirectory 'C:\AIOps_Agent_bak' -Wait -NoNewWindow
