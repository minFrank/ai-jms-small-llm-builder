$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' }
Write-Output ("count=" + @($p).Count)
foreach ($x in $p) { Write-Output ($x.ProcessId.ToString() + " | " + $x.CreationDate.ToString() + " | " + $x.CommandLine) }
