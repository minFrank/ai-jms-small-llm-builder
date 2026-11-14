import subprocess
q = "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*batch_runner*' } | ForEach-Object { \"{0}|{1}|{2}\" -f $_.ProcessId, $_.CreationDate, $_.CommandLine }"
out = subprocess.run(["powershell", "-NoProfile", "-Command", q], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("STDOUT:")
print(out.stdout)
print("STDERR:")
print(out.stderr)
