"""Offline tests must not touch the network. Any socket a test opens fails it.

CI additionally runs these tests inside `unshare -rn` (no network namespace),
so the guarantee holds even for code that bypasses the socket module.
"""
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


class NetworkUsed(AssertionError):
    pass


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise NetworkUsed("offline code opened a network socket")
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
