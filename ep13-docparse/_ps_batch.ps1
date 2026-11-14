$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'batch_runner' }
$p | ForEach-Object {
  $cl = $_.CommandLine
  if ($cl.Length -gt 200) { $cl = $cl.Substring(0,200) }
  [PSCustomObject]@{ Pid=$_.ProcessId; Name=$_.Name; Start=$_.CreationDate; Cmd=$cl }
} | Format-List
"COUNT=" + @($p).Count
