Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
  Where-Object { $_.CommandLine -like '*batch_runner*' -or $_.CommandLine -like '*scripts\runner.py*' -or $_.CommandLine -like '*scripts/runner.py*' } |
  Select-Object ProcessId, CreationDate, @{n='CL';e={$_.CommandLine.Substring(0,[Math]::Min(160,$_.CommandLine.Length))}} |
  Format-List
