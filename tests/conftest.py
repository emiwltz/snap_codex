"""Tests use temporary databases and simulated provider transports only."""

import socket

import pytest


@pytest.fixture(autouse=True)
def disable_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled in local tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
