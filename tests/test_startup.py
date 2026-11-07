"""What happens when the server starts."""
from fastapi.testclient import TestClient

import main


def test_server_startup_runs_the_corporate_actions_catch_up(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "catch_up_on_startup", lambda: calls.append("ran"))
    with TestClient(main.app):  # entering the `with` block is what starts the app
        pass
    assert calls == ["ran"]