import pytest
from click.testing import CliRunner

from copernicusmarine_delivery.command_line_interface import cli

COMMANDS = [
    [],
    ["delivery"],
    ["upload"],
    ["delete"],
    ["status"],
    ["list-deliveries"],
]


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: "/".join(c) or "cli")
def test_help_does_not_require_credentials(monkeypatch, command):
    """--help must work even without COPERNICUSMARINE_SERVICE_USERNAME/PASSWORD
    set, since those are only needed once a command actually runs (see
    environment_variables.get_copernicusmarine_username/password)."""
    monkeypatch.delenv("COPERNICUSMARINE_SERVICE_USERNAME", raising=False)
    monkeypatch.delenv("COPERNICUSMARINE_SERVICE_PASSWORD", raising=False)

    runner = CliRunner()
    result = runner.invoke(cli, [*command, "--help"])

    assert result.exit_code == 0
    assert result.exception is None
    assert "Usage:" in result.output
    assert "environment variable is not set" not in result.output
