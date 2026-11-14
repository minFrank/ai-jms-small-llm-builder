$ErrorActionPreference = 'SilentlyContinue'
$procs = Get-CimInstance Win32_Process
foreach ($p in $procs) {
  $c = $p.CommandLine
  if ($null -ne $c -and $c -match 'batch_runner') {
    "{0} | {1} | {2}" -f $p.ProcessId, $p.CreationDate, ($c -replace '\s+',' ')
  }
}
"---- python procs with ep13 in cmdline ----"
foreach ($p in $procs) {
  $c = $p.CommandLine
  if ($null -ne $c -and $c -match 'ep13' -and $c -match '\.py') {
    "{0} | {1} | {2}" -f $p.ProcessId, $p.CreationDate, ($c -replace '\s+',' ')
  }
}
