$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'batch_runner' }
if ($p) { $p | ForEach-Object { "PID=$($_.ProcessId) START=$($_.CreationDate)" } } else { "NONE" }
