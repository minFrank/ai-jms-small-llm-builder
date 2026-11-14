$k = 'batch' + '_runner'
$p = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -like ("*" + $k + "*") -and $_.Name -notlike 'bash*' -and $_.Name -ne 'powershell.exe' })
"BATCHRUNNER_COUNT=" + $p.Count
foreach ($x in $p) { "PID=$($x.ProcessId) NAME=$($x.Name) START=$($x.CreationDate)" }
$py = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' })
"PYTHON_COUNT=" + $py.Count
foreach ($x in $py) {
  $c = $x.CommandLine
  if (-not $c) { $c = '(null)' }
  $c = $c -replace '\s+', ' '
  if ($c.Length -gt 200) { $c = $c.Substring(0, 200) }
  "PYPID=$($x.ProcessId) START=$($x.CreationDate) CMD=$c"
}
