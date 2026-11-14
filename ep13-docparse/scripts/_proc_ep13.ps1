$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'batch_runner' }
if (-not $procs) { Write-Output 'BATCH_RUNNER_COUNT=0' }
foreach ($p in $procs) {
  Write-Output ("BATCH pid={0} created={1}" -f $p.ProcessId, $p.CreationDate)
}
$kids = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'runner\.py' }
foreach ($p in $kids) {
  Write-Output ("CELL pid={0} created={1}" -f $p.ProcessId, $p.CreationDate)
}
