Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Select-Object ProcessId, CommandLine |
    Export-Csv -NoTypeInformation -Encoding utf8 -Path temp_ps.csv
