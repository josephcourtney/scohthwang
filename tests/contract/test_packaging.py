"""Packaging and entry-point smoke tests."""

from __future__ import annotations

import os
import subprocess  # ruff: ignore[suspicious-subprocess-import] - packaging contract tests intentionally execute local build/install commands.
import sys
from pathlib import Path

import pytest

import scohthwang


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command and capture text output for assertions."""
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - test passes explicit argv list and does not invoke a shell.
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )


@pytest.mark.contract
@pytest.mark.medium
@pytest.mark.smoke
def test_wheel_installs_and_console_script_runs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dist_dir = tmp_path / "dist"
    venv_dir = tmp_path / "venv"
    build_env = os.environ.copy()
    build_env["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")

    _run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        cwd=repo_root,
        env=build_env,
    )
    wheel_path = next(dist_dir.glob("scohthwang-*.whl"))

    _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=repo_root)

    venv_bin = venv_dir / "bin"
    venv_python = venv_bin / "python"
    cli_path = venv_bin / "scohthwang"

    _run([str(venv_python), "-m", "pip", "install", str(wheel_path)], cwd=repo_root)

    import_result = _run(
        [
            str(venv_python),
            "-c",
            "import scohthwang; print(scohthwang.__version__)",
        ],
        cwd=repo_root,
    )
    assert import_result.stdout.strip() == scohthwang.__version__

    version_result = _run([str(cli_path), "--version"], cwd=repo_root)
    assert version_result.stdout.strip() == f"scohthwang {scohthwang.__version__}"

    api_result = _run([str(cli_path), "--list-api"], cwd=repo_root)
    assert set(api_result.stdout.splitlines()) == set(scohthwang.__all__)
