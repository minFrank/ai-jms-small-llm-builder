# -*- coding: utf-8 -*-
"""socket 层出网拦截。EP11_OFFLINE=1 时由 bench_cell 在第一条引擎 import 之前加载。

效果等价于「拔网线」的出网层面：任何对外 connect / DNS 都被拒绝并记录。
记录追加到 net_blocked.json（append-only），报告里原样引用。
"""
import json
import os
import socket
import time

_LOG = os.environ.get("EP11_NETLOG", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "net_blocked.json"))
# 本机代理端口：Windows 上 urllib/requests 会读注册表代理，连接落到 127.0.0.1:<proxy>，
# 只放行「非回环 host」拦不住它 —— 回环 + 代理端口同样要拦。
PROXY_PORTS = {7897, 7890, 1080, 8080, 8118, 10808, 10809}
_recorded = []
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo
_real_ghe = socket.gethostbyname_ex
_real_gbn = socket.gethostbyname


def _host_port(addr):
    if isinstance(addr, tuple) and len(addr) >= 2:
        return str(addr[0]), int(addr[1])
    return str(addr), 0


def _is_local(host):
    return host in ("127.0.0.1", "::1", "localhost", "0.0.0.0")


def _record(kind, addr):
    _recorded.append({"kind": kind, "addr": str(addr), "ts": time.time()})
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, "addr": str(addr),
                                "ts": round(time.time(), 3),
                                "pid": os.getpid()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _blocked(kind, addr):
    _record(kind, addr)
    raise OSError(10013, "EP11_OFFLINE: outbound %s to %s blocked by offline guard"
                  % (kind, addr))


def _denied(addr):
    host, port = _host_port(addr)
    if _is_local(host):
        return port in PROXY_PORTS
    return True


def guard_connect(self, addr):
    if not _denied(addr):
        return _real_connect(self, addr)
    _blocked("connect", addr)


def guard_connect_ex(self, addr):
    if not _denied(addr):
        return _real_connect_ex(self, addr)
    _blocked("connect_ex", addr)
    return 1


def guard_getaddrinfo(host, *a, **kw):
    if not _is_local(str(host)):
        _blocked("getaddrinfo", host)
    return _real_getaddrinfo(host, *a, **kw)


def guard_gbn(host):
    if not _is_local(str(host)):
        _blocked("gethostbyname", host)
    return _real_gbn(host)


def guard_ghe(host):
    if not _is_local(str(host)):
        _blocked("gethostbyname_ex", host)
    return _real_ghe(host)


socket.socket.connect = guard_connect
socket.socket.connect_ex = guard_connect_ex
socket.getaddrinfo = guard_getaddrinfo
socket.gethostbyname = guard_gbn
socket.gethostbyname_ex = guard_ghe
ACTIVE = True
