from __future__ import annotations

import automation.cli.main as cli


def test_main_runs_uvicorn_with_expected_settings(monkeypatch):
    calls = {}
    monkeypatch.setattr(cli.settings, "host", "127.0.0.1")
    monkeypatch.setattr(cli.settings, "port", 9000)
    monkeypatch.setattr(cli.settings, "debug", True)
    monkeypatch.setattr(
        cli.uvicorn,
        "run",
        lambda app, host, port, reload, log_level: calls.update(
            {
                "app": app,
                "host": host,
                "port": port,
                "reload": reload,
                "log_level": log_level,
            }
        ),
    )

    cli.main()

    assert calls == {
        "app": "automation.main:app",
        "host": "127.0.0.1",
        "port": 9000,
        "reload": True,
        "log_level": "debug",
    }
