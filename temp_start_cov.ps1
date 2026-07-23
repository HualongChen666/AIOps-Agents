$proc = Start-Process -FilePath python -ArgumentList 'scripts/run_core_api_infrastructure_tests.py' `
    -WorkingDirectory 'C:\AIOps_Agent_bak' `
    -RedirectStandardOutput 'cov_clean_omit.log' `
    -RedirectStandardError 'cov_clean_omit_err.log' `
    -NoNewWindow -PassThru
$proc | Select-Object Id, StartTime | Export-Csv -NoTypeInformation -Path 'cov_proc.csv' -Encoding utf8
