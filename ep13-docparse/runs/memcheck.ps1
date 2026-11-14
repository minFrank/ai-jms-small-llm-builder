$os = Get-CimInstance Win32_OperatingSystem
Write-Host ("MEM_FREE_GB=" + [math]::Round($os.FreePhysicalMemory/1MB,1))
Write-Host ("MEM_TOTAL_GB=" + [math]::Round($os.TotalVisibleMemorySize/1MB,1))
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
  $cmd = $_.CommandLine
  if ($cmd -eq $null) { $cmd = "" }
  if ($cmd.Length -gt 110) { $cmd = $cmd.Substring(0,110) }
  Write-Host ("PY pid=" + $_.ProcessId + " mem=" + [math]::Round($_.WorkingSetSize/1MB,0) + "MB " + $cmd)
}
