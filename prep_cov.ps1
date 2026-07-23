Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -notlike '*lsp_server.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Remove-Item -Path ".coverage*" -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path coverage.json) { Remove-Item -Path coverage.json -Force -ErrorAction SilentlyContinue }
if (Test-Path coverage.xml) { Remove-Item -Path coverage.xml -Force -ErrorAction SilentlyContinue }
if (Test-Path htmlcov) { Remove-Item -Path htmlcov -Recurse -Force -ErrorAction SilentlyContinue }

$proc = Start-Process -FilePath python -ArgumentList 'scripts/run_core_api_infrastructure_tests.py' `
    -WorkingDirectory 'C:\AIOps_Agent_bak' `
    -RedirectStandardOutput 'cov_clean_omit.log' `
    -RedirectStandardError 'cov_clean_omit_err.log' `
    -NoNewWindow -PassThru
$proc | Select-Object Id, StartTime | Export-Csv -NoTypeInformation -Path 'cov_proc.csv' -Encoding utf8
