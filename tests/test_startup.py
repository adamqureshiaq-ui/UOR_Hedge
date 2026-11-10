"""What happens when the server starts."""
from fastapi.testclient import TestClient

import main


def start_server(monkeypatch):
    """Starts the app with its startup steps replaced by fakes; returns the steps in the order they ran."""
    steps = []
    monkeypatch.setattr(main, "upgrade_database", lambda: steps.append("migrations"))
    monkeypatch.setattr(main, "catch_up_on_startup", lambda: steps.append("catch-up"))
    with TestClient(main.app):  # entering the `with` block is what starts the app
        pass
    return steps


def test_server_startup_runs_the_corporate_actions_catch_up(monkeypatch):
    assert "catch-up" in start_server(monkeypatch)


def test_server_startup_applies_migrations_first(monkeypatch):
    # The catch-up reads and writes tables, so they must be up to date before it runs
    assert start_server(monkeypatch)[0] == "migrations"