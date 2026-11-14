$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'batch_runner' }
if ($p) { $p | ForEach-Object { "PID=$($_.PID) START=$($_.CreationDate) CMD=$($_.CommandLine)" } } else { "NO_BATCH_RUNNER" }
