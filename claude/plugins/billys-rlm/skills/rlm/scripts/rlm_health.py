#!/usr/bin/env python3
"""
rlm_health.py — capability probe for the RLM plugin.

Reports Python version, rlms availability, available backends, and sandbox support
so the skill can decide whether to use the canonical runner or the Claude-native fallback.

Exits 0 always. The skill reads the JSON output, not the exit code.
"""

import json
import os
import sys


def main() -> None:
    result = {
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "python_supported": sys.version_info >= (3, 11),
        "rlms_installed": False,
        "rlms_version": None,
        "available_backends": [],
        "sandbox_support": {
            "local": False,
            "ipython_in_process": False,
            "ipython_subprocess": False,
            "docker": False,
        },
        "anthropic_key_present": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "recommended_runner": "native",
    }

    try:
        import rlm  # noqa: F401
        from rlm import RLM  # noqa: F401
        result["rlms_installed"] = True
        try:
            import importlib.metadata as md
            result["rlms_version"] = md.version("rlms")
        except Exception:
            result["rlms_version"] = "unknown"
    except Exception as exc:
        result["rlms_import_error"] = str(exc)

    if result["rlms_installed"]:
        try:
            import rlm.environments.local_repl  # noqa: F401
            result["sandbox_support"]["local"] = True
        except Exception:
            pass
        try:
            import rlm.environments.ipython_repl  # noqa: F401
            result["sandbox_support"]["ipython_in_process"] = True
            result["sandbox_support"]["ipython_subprocess"] = True
        except Exception:
            pass
        try:
            import rlm.environments.docker_repl  # noqa: F401
            result["sandbox_support"]["docker"] = True
        except Exception:
            pass

        try:
            from rlm.core import lm_handler  # noqa: F401
            result["available_backends"] = ["anthropic", "openai", "gemini", "azure"]
        except Exception:
            result["available_backends"] = []

    if (
        result["python_supported"]
        and result["rlms_installed"]
        and result["anthropic_key_present"]
        and result["sandbox_support"]["ipython_subprocess"]
    ):
        result["recommended_runner"] = "canonical"

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
