$os = Get-CimInstance Win32_OperatingSystem
Write-Host ("PHYS_TOTAL_GB=" + [math]::Round($os.TotalVisibleMemorySize/1MB,1))
Write-Host ("PHYS_FREE_GB=" + [math]::Round($os.FreePhysicalMemory/1MB,1))
Write-Host ("COMMIT_TOTAL_GB=" + [math]::Round($os.TotalVirtualMemorySize/1MB,1))
Write-Host ("COMMIT_FREE_GB=" + [math]::Round($os.FreeVirtualMemory/1MB,1))
$pf = Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue
if ($pf) { foreach ($p in $pf) { Write-Host ("PAGEFILE=" + $p.Name + " alloc=" + $p.AllocatedBaseSize + "MB") } }
else { Write-Host "PAGEFILE=auto" }
$cs = Get-CimInstance Win32_ComputerSystem
Write-Host ("AUTOMANAGE_PAGEFILE=" + $cs.AutomaticManagedPagefile)
