from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from databricks_integration.smoke import cli_json, load_config, run


def test_load_config_uses_no_secret_material() -> None:
    config = load_config(Path("configs/databricks.toml"))
    assert config["profile"]
    assert "token" not in config
    assert "password" not in config


def test_cli_json_invokes_explicit_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == ["databricks", "version", "--profile", "test", "--output", "json"]
        return subprocess.CompletedProcess(args, 0, '{"ok": true}', "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli_json(["version"], "test") == {"ok": True}


def test_run_executes_remote_query(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[databricks]\nprofile="test"\nwarehouse_id="wh"\n'
        'wait_timeout="50s"\npoll_interval="0s"\n'
    )
    calls: list[list[str]] = []
    responses = [
        [{"id": "wh", "enable_serverless_compute": True}],
        {
            "statement_id": "stmt",
            "status": {"state": "SUCCEEDED"},
            "result": {"data_array": [["1"]]},
        },
    ]

    def fake_cli(args: list[str], profile: str) -> object:
        calls.append(args)
        return responses.pop(0)

    monkeypatch.setattr("databricks_integration.smoke.cli_json", fake_cli)
    assert run(cfg)["rows"] == [["1"]]
    body = json.loads(calls[1][calls[1].index("--json") + 1])
    assert body["statement"] == "SELECT 1 AS spark_smoke"


def test_profile_override_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[databricks]\nprofile="config"\nwarehouse_id="wh"\n'
        'wait_timeout="50s"\npoll_interval="0s"\n'
    )
    profiles: list[str] = []

    def fake_cli(args: list[str], profile: str) -> object:
        profiles.append(profile)
        if args == ["warehouses", "list"]:
            return [{"id": "wh"}]
        return {
            "statement_id": "stmt",
            "status": {"state": "SUCCEEDED"},
            "result": {"data_array": [["1"]]},
        }

    monkeypatch.setattr("databricks_integration.smoke.cli_json", fake_cli)
    monkeypatch.setenv("DATABRICKS_CONFIG_PROFILE", "environment")
    run(cfg, "command-line")
    assert profiles == ["command-line", "command-line"]
    profiles.clear()
    run(cfg)
    assert profiles == ["environment", "environment"]
