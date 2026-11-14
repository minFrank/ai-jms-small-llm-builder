# ep13 页面文件扩容 84GB -> 128GB（管理员执行，A 方案）
$log = "D:\study\ai-jms\ep13-docparse\runs\pagefile_resize_result.txt"
try {
    $lines = @()
    $lines += "time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $cs = Get-CimInstance Win32_ComputerSystem
    $lines += "before: AutoManaged=$($cs.AutomaticManagedPagefile)"
    Get-CimInstance Win32_PageFileUsage | ForEach-Object { $lines += "before: $($_.Name) Alloc=$($_.AllocatedBaseSize)MB" }

    if ($cs.AutomaticManagedPagefile) {
        Set-CimInstance -InputObject $cs -Property @{AutomaticManagedPagefile=$false}
        $lines += "AutoManaged -> False  [OK]"
    }
    $pf = Get-CimInstance Win32_PageFileSetting -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "D:*" }
    if (-not $pf) {
        New-CimInstance -ClassName Win32_PageFileSetting -Property @{Name="D:\pagefile.sys"; InitialSize=131072; MaximumSize=131072} | Out-Null
        $lines += "created D:\pagefile.sys 131072MB [OK]"
    } else {
        Set-CimInstance -InputObject $pf -Property @{InitialSize=131072; MaximumSize=131072}
        $lines += "updated D:\pagefile.sys -> 131072MB [OK]"
    }
    # 复读
    $cs2 = Get-CimInstance Win32_ComputerSystem
    $lines += "after: AutoManaged=$($cs2.AutomaticManagedPagefile)"
    Get-CimInstance Win32_PageFileSetting -ErrorAction SilentlyContinue | ForEach-Object { $lines += "after: Setting $($_.Name) Init=$($_.InitialSize) Max=$($_.MaximumSize)" }
    $lines += "RESULT=SUCCESS（完全生效可能需重启；在线扩通常即时提高 commit limit）"
    $lines -join "`r`n" | Set-Content -Path $log -Encoding UTF8
} catch {
    "RESULT=FAIL: $($_.Exception.Message)`r`n$($_.InvocationInfo.PositionMessage)" | Set-Content -Path $log -Encoding UTF8
}
