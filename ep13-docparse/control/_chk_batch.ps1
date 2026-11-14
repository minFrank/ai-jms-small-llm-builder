Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'batch_runner' } | ForEach-Object {
  "{0}|{1}|{2}" -f $_.ProcessId, $_.CreationDate, $_.CommandLine
}
