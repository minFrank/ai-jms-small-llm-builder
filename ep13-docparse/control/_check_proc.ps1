$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' }
if ($procs) {
  $procs | ForEach-Object { "PID=$($_.ProcessId) START=$($_.CreationDate)" }
} else {
  "NONE"
}
