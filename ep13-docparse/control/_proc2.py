import subprocess
q = "Get-CimInstance Win32_Process -Filter 'ProcessId=38408' | ForEach-Object { '{0} | {1} | {2}' -f $_.ProcessId, $_.Name, $_.CommandLine }"
out = subprocess.run(["powershell", "-NoProfile", "-Command", q], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("OUT:", out.stdout.strip())
print("ERR:", out.stderr.strip())
q2 = "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*ep13*' -and $_.Name -like '*python*' } | ForEach-Object { '{0} | {1} | {2}' -f $_.ProcessId, $_.CreationDate, $_.CommandLine }"
out2 = subprocess.run(["powershell", "-NoProfile", "-Command", q2], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("PY_EP13:")
print(out2.stdout.strip())
