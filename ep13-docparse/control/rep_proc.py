import sys
try:
    import win32com.client
except Exception as e:
    print("NO_WIN32COM", e); sys.exit(0)
try:
    wmi = win32com.client.GetObject("winmgmts:root\\cimv2")
    procs = wmi.ExecQuery("SELECT ProcessId, Name, CommandLine, CreationDate FROM Win32_Process WHERE Name LIKE 'python%'")
    n = 0
    for p in procs:
        cl = p.CommandLine or ""
        if "batch_runner" in cl:
            print("ALIVE PID", p.ProcessId, "START", p.CreationDate)
            n += 1
    print("MATCHED", n, "TOTAL_PY", len(procs))
    for p in procs:
        print("  PY", p.ProcessId, (p.CommandLine or "")[:200])
except Exception as e:
    print("WMI_ERR", repr(e))
