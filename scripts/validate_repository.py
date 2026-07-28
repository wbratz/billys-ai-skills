#!/usr/bin/env python3
"""Validate the public contracts shared by both plugin marketplaces."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []


def error(message: str) -> None:
    ERRORS.append(message)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        error(f"{path.relative_to(ROOT)}: {exc}")
        return {}


def require_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        error(f"{label} must be a non-empty string")


def validate_skill(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        error(f"{path.relative_to(ROOT)}: missing YAML frontmatter")
        return
    frontmatter = text.split("---", 2)[1]
    for field in ("name", "description"):
        if not re.search(rf"(?m)^{field}:\s*\S", frontmatter):
            error(f"{path.relative_to(ROOT)}: missing {field} in frontmatter")


def validate_claude() -> None:
    marketplace_path = ROOT / "claude/.claude-plugin/marketplace.json"
    marketplace = load_json(marketplace_path)
    require_text(marketplace.get("name"), "Claude marketplace name")

    for entry in marketplace.get("plugins", []):
        name = entry.get("name")
        source = entry.get("source")
        require_text(name, "Claude plugin name")
        require_text(source, f"Claude plugin {name} source")
        if not isinstance(source, str):
            continue
        plugin_dir = (marketplace_path.parent.parent / source).resolve()
        manifest_path = plugin_dir / ".claude-plugin/plugin.json"
        if not manifest_path.is_file():
            error(f"Claude plugin {name}: missing {manifest_path.relative_to(ROOT)}")
            continue
        manifest = load_json(manifest_path)
        if manifest.get("name") != name:
            error(f"Claude plugin {name}: manifest name does not match")
        if manifest.get("version") != entry.get("version"):
            error(f"Claude plugin {name}: marketplace and manifest versions differ")
        if not (plugin_dir / "README.md").is_file():
            error(f"Claude plugin {name}: missing README.md")


def validate_codex() -> None:
    marketplace_path = ROOT / "openai/.agents/plugins/marketplace.json"
    marketplace = load_json(marketplace_path)
    require_text(marketplace.get("name"), "Codex marketplace name")

    for entry in marketplace.get("plugins", []):
        name = entry.get("name")
        source = entry.get("source", {})
        require_text(name, "Codex plugin name")
        if source.get("source") != "local":
            error(f"Codex plugin {name}: repository entries must use a local source")
            continue
        source_path = source.get("path")
        require_text(source_path, f"Codex plugin {name} source path")
        if not isinstance(source_path, str):
            continue
        plugin_dir = (marketplace_path.parent.parent.parent / source_path).resolve()
        manifest_path = plugin_dir / ".codex-plugin/plugin.json"
        if not manifest_path.is_file():
            error(f"Codex plugin {name}: missing {manifest_path.relative_to(ROOT)}")
            continue
        manifest = load_json(manifest_path)
        if manifest.get("name") != name:
            error(f"Codex plugin {name}: manifest name does not match")
        if plugin_dir.name != name:
            error(f"Codex plugin {name}: folder and manifest names differ")
        require_text(manifest.get("version"), f"Codex plugin {name} version")
        require_text(manifest.get("description"), f"Codex plugin {name} description")
        skills_path = manifest.get("skills")
        if skills_path and not (plugin_dir / skills_path).is_dir():
            error(f"Codex plugin {name}: declared skills path does not exist")


def validate_repository() -> None:
    validate_claude()
    validate_codex()

    skills = sorted(ROOT.glob("claude/plugins/**/skills/*/SKILL.md"))
    skills += sorted(ROOT.glob("openai/plugins/**/skills/*/SKILL.md"))
    if not skills:
        error("No plugin skills found")
    for path in skills:
        validate_skill(path)

    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        if "[TODO:" in path.read_text(encoding="utf-8"):
            error(f"{path.relative_to(ROOT)}: unresolved TODO placeholder")


if __name__ == "__main__":
    validate_repository()
    if ERRORS:
        print("Repository validation failed:")
        for issue in ERRORS:
            print(f"  - {issue}")
        sys.exit(1)
    print("Repository validation passed.")
