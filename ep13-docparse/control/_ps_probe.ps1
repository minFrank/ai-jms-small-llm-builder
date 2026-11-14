$ErrorActionPreference = 'SilentlyContinue'
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' } | ForEach-Object {
  "{0}|{1}|{2}" -f $_.ProcessId, $_.Name, $_.CommandLine
}
"---MARK---"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ep13*' } | ForEach-Object {
  "{0}|{1}|{2}" -f $_.ProcessId, $_.Name, $_.CommandLine
}
