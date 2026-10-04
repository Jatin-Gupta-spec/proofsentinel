"""Tests for the command-line interface (Stage 2)."""

import runpy
import sys
from pathlib import Path

import pytest

from proofsentinel.cli import ExitCode, build_parser, main


@pytest.fixture(autouse=True)
def _plain_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Newer Pythons can colorize argparse output; keep test output plain and stable."""
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("PYTHON_COLORS", "0")
    monkeypatch.delenv("FORCE_COLOR", raising=False)


UNIMPLEMENTED_INVOCATIONS = [
    ["validate", "manifest.toml"],
    ["run", "manifest.toml", "--output", "evidence-out"],
    ["verify-evidence", "evidence-out"],
]

BAD_USAGE_INVOCATIONS = [
    [],
    ["no-such-command"],
    ["validate"],
    ["run", "manifest.toml"],
    ["run", "--output", "evidence-out"],
    ["verify-evidence"],
    ["validate", "manifest.toml", "extra"],
    ["validate", "manifest.toml", "--no-such-option"],
]


def test_exit_codes_match_the_contract() -> None:
    assert ExitCode.OK == 0
    assert ExitCode.CHECKS_FAILED == 1
    assert ExitCode.ERROR == 2
    assert ExitCode.USAGE == 3


def test_top_level_help_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    captured = capsys.readouterr()
    assert "usage: proofsentinel" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize("command", ["validate", "run", "verify-evidence"])
def test_subcommand_help_returns_zero(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([command, "--help"]) == 0
    captured = capsys.readouterr()
    assert f"usage: proofsentinel {command}" in captured.out
    assert captured.err == ""


@pytest.mark.parametrize("argv", BAD_USAGE_INVOCATIONS)
def test_bad_usage_returns_three_without_traceback(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == ExitCode.USAGE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("argv", UNIMPLEMENTED_INVOCATIONS)
def test_unimplemented_commands_fail_closed(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    result = main(argv)
    assert result == ExitCode.ERROR
    assert result != ExitCode.OK
    assert "not implemented" in capsys.readouterr().err


def test_paths_are_parsed_but_not_opened() -> None:
    namespace = build_parser().parse_args(["validate", "missing-manifest.toml"])
    assert isinstance(namespace.manifest, Path)
    assert namespace.manifest.name == "missing-manifest.toml"
    assert not namespace.manifest.exists()


def test_control_characters_are_not_echoed_raw(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["bad\x1bcommand"]) == ExitCode.USAGE
    error_text = capsys.readouterr().err
    assert "\x1b" not in error_text
    assert "\\x1b" in error_text


def test_newlines_in_arguments_cannot_forge_error_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["bad\nproofsentinel: error: forged"]) == ExitCode.USAGE
    error_lines = capsys.readouterr().err.splitlines()
    forged = [line for line in error_lines if line.startswith("proofsentinel: error: forged")]
    assert forged == []


def test_module_entry_point_returns_usage_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["proofsentinel"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("proofsentinel.__main__", run_name="__main__")
    assert excinfo.value.code == 3


def test_module_entry_point_help_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["proofsentinel", "--help"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("proofsentinel.__main__", run_name="__main__")
    assert excinfo.value.code == 0