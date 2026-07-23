$csv = if (Test-Path cov_proc_config.csv) { 'cov_proc_config.csv' } else { 'cov_proc.csv' }
$procId = Get-Content $csv | Select-Object -Skip 1 | ForEach-Object { ($_ -split ',')[0].Trim('"') } | Select-Object -First 1
$alive = if (Get-Process -Id $procId -ErrorAction SilentlyContinue) { 'RUNNING' } else { 'DONE' }
@{
    pid        = $procId
    status     = $alive
    checked_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
} | ConvertTo-Json | Set-Content cov_status.json
