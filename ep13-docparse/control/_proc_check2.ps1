$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' }
if ($p) { $p | ForEach-Object { "ALIVE pid=$($_.ProcessId) start=$($_.CreationDate)" } } else { "NO_BATCH_RUNNER" }
$h = Get-Process -Id 7832 -ErrorAction SilentlyContinue
if ($h) { "PID7832_ALIVE name=$($h.ProcessName) start=$($h.StartTime)" } else { "PID7832_DEAD" }
