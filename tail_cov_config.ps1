$text = (Get-Content cov_with_config.log -Tail 30) -join "`r`n"
@{
    tail = $text
    written_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
} | ConvertTo-Json | Set-Content cov_tail_config.json
