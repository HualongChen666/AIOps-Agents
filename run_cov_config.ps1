Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -notlike '*lsp_server.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Remove-Item -Path ".coverage" -Force -ErrorAction SilentlyContinue
Remove-Item -Path ".coverage.*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "coverage.json" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "coverage.xml" -Force -ErrorAction SilentlyContinue
if (Test-Path htmlcov) { Remove-Item -Path htmlcov -Recurse -Force -ErrorAction SilentlyContinue }

$proc = Start-Process -FilePath python -ArgumentList 'scripts/run_core_api_infrastructure_tests.py' `
    -WorkingDirectory 'C:\AIOps_Agent_bak' `
    -RedirectStandardOutput 'cov_with_config.log' `
    -RedirectStandardError 'cov_with_config_err.log' `
    -NoNewWindow -PassThru
$proc | Select-Object Id, StartTime | Export-Csv -NoTypeInformation -Path 'cov_proc_config.csv' -Encoding utf8
