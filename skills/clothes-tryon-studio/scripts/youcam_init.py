"""Python Environment bootstrap: virtual environment setup and dependency checks for youcam agent skill."""

import json
import os
import subprocess
import sys

from constants import _REQUIREMENTS, _VENV_DIR

_MISSING_DEPS = []
try:
    import requests
except ImportError:
    requests = None
    _MISSING_DEPS.append("requests")
try:
    import yaml
except ImportError:
    yaml = None
    _MISSING_DEPS.append("PyYAML")


def _venv_python(venv_dir: str) -> str:
    """Return the path to the python executable inside a virtual environment.

    Returns:
        str: Path to the venv's python executable, OS-appropriate.
    """
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def setup_env() -> int:
    """
    Create a project local virtual environment named .venv and install requirements.txt into it.

    Returns:
        int: 0 on success.
    """
    print(f"[setup] current interpreter: {sys.executable}, Python {sys.version.split()[0]}")
    in_venv = sys.prefix != sys.base_prefix
    print(f"[setup] running inside a virtual environment: {in_venv}")

    if os.path.isdir(_VENV_DIR):
        print(f"[setup] virtual environment already exists at {_VENV_DIR}")
    else:
        print(f"[setup] creating virtual environment at {_VENV_DIR} ...")
        subprocess.run([sys.executable, "-m", "venv", _VENV_DIR], check=True)

    venv_python = _venv_python(_VENV_DIR)
    print(f"[setup] installing dependencies from {_REQUIREMENTS} ...")
    subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([venv_python, "-m", "pip", "install", "-r", _REQUIREMENTS], check=True)

    activate_hint = (
        rf"{_VENV_DIR}\Scripts\activate" if os.name == "nt" else f"source {_VENV_DIR}/bin/activate"
    )
    print(
        "\nWARNING: these dependencies were installed into a project local virtual environment, "
        "not your system or global Python.\n"
        f'Call "{venv_python}" youcam_core.py <command> to use it directly.\n'
        f"Or activate it first by running: {activate_hint}\n"
        "Invoking `python youcam_core.py ...` with a different interpreter will not see "
        "these installed packages.",
        file=sys.stderr,
    )
    return 0


def _dependency_error() -> int:
    """Print a structured error for missing dependencies.

    Returns:
        int: Exit code 3.
    """
    print(
        json.dumps(
            {
                "error": "Missing required dependencies for youcam agent skill.",
                "hint": "Run `python youcam_core.py setup` to create a virtual environment and install "
                "requirements.txt, or `pip install -r requirements.txt` yourself.",
                "details": f"{_MISSING_DEPS}",
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 3
