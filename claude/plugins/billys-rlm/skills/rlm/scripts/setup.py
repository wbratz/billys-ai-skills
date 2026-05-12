#!/usr/bin/env python3
"""
setup.py - prereq check & setup helper for the billys/rlm plugin.

Reports the status of every prerequisite as a table. For each missing or
broken piece, prints the exact command the user should run. Does NOT install
anything automatically.

Exit codes:
  0 - canonical runner is ready
  1 - some prereqs missing; native fallback usable
  2 - unrecoverable (e.g., no Python at all)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

OK = "[OK]"
MISS = "[MISSING]"
WARN = "[WARN]"


def color_status(status: str) -> str:
    return status


def check_python() -> dict:
    v = sys.version_info
    ok = v >= (3, 11)
    return {
        "name": "Python 3.11+",
        "status": OK if ok else MISS,
        "detail": f"running {v.major}.{v.minor}.{v.micro}",
        "fix": None if ok else (
            "Install Python 3.11 or newer:\n"
            "  - Windows:  https://www.python.org/downloads/  (or `winget install Python.Python.3.12`)\n"
            "  - macOS:    `brew install python@3.12`\n"
            "  - Linux:    use your distro's package manager\n"
            "Then re-run setup with the new interpreter (e.g., `py -3.12 setup.py`)."
        ),
    }


def check_rlms() -> dict:
    try:
        import rlm  # noqa: F401
        try:
            import importlib.metadata as md
            ver = md.version("rlms")
        except Exception:
            ver = "unknown"
        return {"name": "rlms package", "status": OK, "detail": f"v{ver}", "fix": None}
    except Exception as exc:
        return {
            "name": "rlms package",
            "status": MISS,
            "detail": str(exc),
            "fix": "python -m pip install --upgrade rlms",
        }


def check_pypdf() -> dict:
    try:
        import pypdf  # noqa: F401
        return {"name": "pypdf (optional, PDF support)", "status": OK, "detail": "importable", "fix": None}
    except Exception:
        return {
            "name": "pypdf (optional, PDF support)",
            "status": WARN,
            "detail": "not installed",
            "fix": "python -m pip install pypdf",
        }


def check_anthropic_key() -> dict:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"name": "ANTHROPIC_API_KEY", "status": OK, "detail": "set", "fix": None}
    return {
        "name": "ANTHROPIC_API_KEY",
        "status": MISS,
        "detail": "not set",
        "fix": (
            "Export your key in your shell. Examples:\n"
            "  PowerShell: $env:ANTHROPIC_API_KEY = 'sk-ant-...'\n"
            "  bash/zsh:   export ANTHROPIC_API_KEY='sk-ant-...'\n"
            "Get a key at: https://console.anthropic.com/"
        ),
    }


def check_log_dir(plugin_root: Path) -> dict:
    target = Path.cwd() / ".rlm" / "logs"
    try:
        target.mkdir(parents=True, exist_ok=True)
        test_file = target / ".write-test"
        test_file.write_text("ok")
        test_file.unlink()
        return {"name": ".rlm/logs/ writable", "status": OK, "detail": str(target), "fix": None}
    except Exception as exc:
        return {
            "name": ".rlm/logs/ writable",
            "status": MISS,
            "detail": str(exc),
            "fix": f"Ensure {target} is writable, or set RLM_LOG_DIR to a writable path.",
        }


def check_gitignore() -> dict:
    gi = Path.cwd() / ".gitignore"
    if not gi.exists():
        return {
            "name": ".gitignore has .rlm/",
            "status": WARN,
            "detail": "no .gitignore in cwd",
            "fix": "Optional. Add `.rlm/` to your project's .gitignore to keep trajectory logs out of version control.",
        }
    text = gi.read_text(errors="replace")
    if ".rlm" in text or ".rlm/" in text:
        return {"name": ".gitignore has .rlm/", "status": OK, "detail": "found", "fix": None}
    return {
        "name": ".gitignore has .rlm/",
        "status": WARN,
        "detail": "not present",
        "fix": "Optional. Append `.rlm/` to .gitignore:\n  echo '.rlm/' >> .gitignore",
    }


def check_ipykernel() -> dict:
    try:
        import ipykernel  # noqa: F401
        return {"name": "ipykernel (subprocess sandbox)", "status": OK, "detail": "importable", "fix": None}
    except Exception:
        return {
            "name": "ipykernel (subprocess sandbox)",
            "status": WARN,
            "detail": "not installed",
            "fix": "python -m pip install ipykernel  (required for the default IPython subprocess sandbox)",
        }


def main() -> None:
    plugin_root = Path(__file__).resolve().parents[2]

    print("billys/rlm setup check")
    print("=" * 60)

    checks = [
        check_python(),
        check_rlms(),
        check_ipykernel(),
        check_pypdf(),
        check_anthropic_key(),
        check_log_dir(plugin_root),
        check_gitignore(),
    ]

    name_w = max(len(c["name"]) for c in checks) + 2
    for c in checks:
        print(f"  {c['status']:<10} {c['name']:<{name_w}} {c['detail']}")

    missing = [c for c in checks if c["status"] == MISS]
    warnings = [c for c in checks if c["status"] == WARN]

    print()
    if missing:
        print("Missing prerequisites:")
        for c in missing:
            print(f"\n  * {c['name']}")
            for line in c["fix"].splitlines():
                print(f"      {line}")
        print()

    if warnings:
        print("Optional / recommended:")
        for c in warnings:
            print(f"\n  * {c['name']}: {c['detail']}")
            if c["fix"]:
                for line in c["fix"].splitlines():
                    print(f"      {line}")
        print()

    canonical_ready = (
        check_python()["status"] == OK
        and check_rlms()["status"] == OK
        and check_anthropic_key()["status"] == OK
    )

    print("-" * 60)
    if canonical_ready:
        print("Status: canonical runner is READY. /rlm will use rlm_run.py.")
        rc = 0
    elif check_python()["status"] == OK:
        print("Status: canonical runner NOT ready. /rlm will fall back to rlm_native.py")
        print("        (no Python REPL, recursion is prompt-level only).")
        rc = 1
    else:
        print("Status: Python prerequisite missing. Install Python 3.11+ first.")
        rc = 2

    summary = {
        "canonical_ready": canonical_ready,
        "checks": [{k: v for k, v in c.items() if k != "fix"} for c in checks],
        "missing_count": len(missing),
        "warning_count": len(warnings),
    }
    print()
    print("JSON summary:")
    print(json.dumps(summary, indent=2))
    sys.exit(rc)


if __name__ == "__main__":
    main()
