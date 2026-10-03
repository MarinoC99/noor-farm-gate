"""CLAUDE.md rule 1: no network at inference.

Called once, before any model loads. Weights come from models/ only; any attempt to
open a network connection from Python raises instead of silently reaching out.
"""
import os
import socket

_LOCAL = {"127.0.0.1", "::1", "localhost"}


class NetworkBlocked(ConnectionError):
    pass


def enforce():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    def _host(address):
        return address[0] if isinstance(address, tuple) else address

    def guard(original):
        def connect(self, address):
            if self.family != socket.AF_UNIX and _host(address) not in _LOCAL:
                raise NetworkBlocked("network access at inference is blocked (CLAUDE.md rule 1)")
            return original(self, address)
        return connect

    socket.socket.connect = guard(socket.socket.connect)
    socket.socket.connect_ex = guard(socket.socket.connect_ex)

    getaddrinfo = socket.getaddrinfo

    def local_getaddrinfo(host, *args, **kwargs):
        if host not in _LOCAL and host is not None:
            raise NetworkBlocked("name lookup at inference is blocked (CLAUDE.md rule 1)")
        return getaddrinfo(host, *args, **kwargs)

    socket.getaddrinfo = local_getaddrinfo
