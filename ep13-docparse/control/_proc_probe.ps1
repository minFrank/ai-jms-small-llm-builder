$ErrorActionPreference = 'SilentlyContinue'
Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'python') -and ($_.CommandLine -match 'batch_runner|ep13|oxr')
} | ForEach-Object {
  "PID=$($_.ProcessId) PPID=$($_.ParentProcessId) START=$($_.CreationDate) CMD=$($_.CommandLine)"
}
"---PID55820---"
$p = Get-CimInstance Win32_Process -Filter "ProcessId=55820"
if ($p) { "ALIVE PID=$($p.ProcessId) CMD=$($p.CommandLine)" } else { "DEAD 55820" }
"---ALLPYTHON---"
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' } | ForEach-Object {
  "PID=$($_.ProcessId) START=$($_.CreationDate) CMD=$($_.CommandLine)"
}
