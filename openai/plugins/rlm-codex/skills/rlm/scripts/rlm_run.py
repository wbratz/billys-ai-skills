#!/usr/bin/env python3
"""Codex-facing CLI runner for Recursive Language Model workflows."""

from __future__ import annotations

import argparse
import inspect
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any, get_args


IGNORED_DIRS = {".git", "node_modules", ".venv", "dist", "build", ".rlm"}
DEFAULT_CHUNK_SIZE = 12000
DEFAULT_CHUNK_OVERLAP = 500
PDF_SUFFIX = ".pdf"


INSTALL_GUIDANCE = {
    "requires": "Python 3.11+ and the rlms package with IPython support.",
    "install": 'python -m pip install "rlms[ipython]"',
    "note": "Create or activate a Python 3.11 or 3.12 environment before installing.",
}


class RunnerError(Exception):
    def __init__(self, message: str, *, code: str = "runner_error", details: Any = None):
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass
class ContextCollection:
    files: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_files: list[dict[str, str]] = field(default_factory=list)
    ignored_directory_count: int = 0

    @property
    def total_chars(self) -> int:
        return sum(int(item.get("char_count", 0)) for item in self.files)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be 0 or greater")
    return parsed


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def fail_json(message: str, *, code: str = "runner_error", details: Any = None) -> None:
    emit_json(
        {
            "ok": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "install_guidance": INSTALL_GUIDANCE,
        }
    )
    raise SystemExit(1)


class RunnerArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        fail_json(message, code="bad_arguments")


def estimate_batches(chunk_count: int, batch_size: int) -> int:
    if chunk_count <= 0:
        return 0
    return math.ceil(chunk_count / batch_size)


def build_fanout_plan(
    *,
    chunk_count: int,
    batch_size: int,
    max_concurrent_subcalls: int,
    environment: str,
    model: str,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "batch_size": batch_size,
        "chunk_count": chunk_count,
        "estimated_batches": estimate_batches(chunk_count, batch_size),
        "max_concurrent_recursive_subcalls": max_concurrent_subcalls,
        "environment": environment,
        "model": model,
        "warnings": warnings,
    }


def is_ignored_path(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def looks_binary(data: bytes) -> bool:
    sample = data[:4096]
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    allowed_controls = {9, 10, 12, 13}
    control_count = sum(1 for byte in sample if byte < 32 and byte not in allowed_controls)
    return control_count / len(sample) > 0.30


def read_text_file(path: Path) -> tuple[str | None, str | None]:
    data = path.read_bytes()
    if looks_binary(data):
        return None, "binary file"
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace"), "decoded with replacement characters"


def read_pdf_file(path: Path) -> tuple[str | None, str | None]:
    reader_cls = None
    import_error = None

    try:
        from pypdf import PdfReader

        reader_cls = PdfReader
    except Exception as exc:  # pragma: no cover - depends on optional local package
        import_error = exc

    if reader_cls is None:
        try:
            from PyPDF2 import PdfReader

            reader_cls = PdfReader
        except Exception as exc:  # pragma: no cover - depends on optional local package
            import_error = exc

    if reader_cls is None:
        return (
            None,
            "PDF skipped because no optional PDF extractor is installed. "
            f"Install pypdf to include PDFs. Last import error: {import_error}",
        )

    try:
        reader = reader_cls(str(path))
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append(f"\n\n--- PDF page {index} ---\n{text}")
        return "".join(pages).strip(), None
    except Exception as exc:  # pragma: no cover - depends on PDF content
        return None, f"PDF skipped because extraction failed: {exc}"


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[dict[str, int | str]]:
    if not text:
        return []
    if chunk_overlap >= chunk_size:
        raise RunnerError("--chunk-overlap must be smaller than --chunk-size", code="bad_arguments")

    chunks: list[dict[str, int | str]] = []
    step = chunk_size - chunk_overlap
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append({"start": start, "end": end, "text": text[start:end]})
        if end >= len(text):
            break
        start += step
    return chunks


def iter_files_from_path(path: Path, collection: ContextCollection) -> list[Path]:
    if not path.exists():
        collection.warnings.append(f"Context path not found: {path}")
        return []

    if is_ignored_path(path):
        collection.skipped_files.append({"path": str(path), "reason": "ignored path"})
        return []

    if path.is_file():
        return [path]

    if not path.is_dir():
        collection.skipped_files.append({"path": str(path), "reason": "unsupported path type"})
        return []

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(path):
        kept_dirnames: list[str] = []
        for dirname in dirnames:
            if dirname in IGNORED_DIRS:
                collection.ignored_directory_count += 1
            else:
                kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in filenames:
            candidate = Path(dirpath) / filename
            if is_ignored_path(candidate):
                collection.skipped_files.append({"path": str(candidate), "reason": "ignored path"})
                continue
            files.append(candidate)
    return files


def load_file_text(path: Path) -> tuple[str | None, str | None, str]:
    if path.suffix.lower() == PDF_SUFFIX:
        text, warning = read_pdf_file(path)
        return text, warning, "pdf"
    text, warning = read_text_file(path)
    return text, warning, "text"


def collect_context(
    context_paths: list[str],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    cwd: Path | None = None,
) -> ContextCollection:
    cwd = cwd or Path.cwd()
    collection = ContextCollection()
    resolved_inputs = [
        (Path(item).expanduser() if Path(item).expanduser().is_absolute() else cwd / item)
        for item in context_paths
    ]

    files: list[Path] = []
    for input_path in resolved_inputs:
        files.extend(iter_files_from_path(input_path.resolve(strict=False), collection))

    for path in sorted(set(files), key=lambda item: str(item).lower()):
        text, warning, kind = load_file_text(path)
        if warning:
            collection.warnings.append(f"{path}: {warning}")
        if text is None:
            collection.skipped_files.append({"path": str(path), "reason": warning or "unreadable"})
            continue

        file_chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        file_record = {
            "path": str(path),
            "kind": kind,
            "char_count": len(text),
            "chunk_count": len(file_chunks),
        }
        collection.files.append(file_record)

        for index, chunk in enumerate(file_chunks):
            chunk_id = f"chunk-{len(collection.chunks) + 1:06d}"
            collection.chunks.append(
                {
                    "id": chunk_id,
                    "source_path": str(path),
                    "chunk_index": index,
                    "chunks_in_source": len(file_chunks),
                    "char_start": chunk["start"],
                    "char_end": chunk["end"],
                    "text": chunk["text"],
                }
            )

    return collection


def context_summary(collection: ContextCollection) -> dict[str, Any]:
    return {
        "file_count": len(collection.files),
        "chunk_count": len(collection.chunks),
        "total_chars": collection.total_chars,
        "skipped_file_count": len(collection.skipped_files),
        "ignored_directory_count": collection.ignored_directory_count,
        "ignored_directories": sorted(IGNORED_DIRS),
        "files": collection.files,
        "skipped_files": collection.skipped_files,
    }


def build_context_payload(
    *,
    task_prompt: str,
    collection: ContextCollection,
    fanout_plan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task": task_prompt,
        "context_files": collection.files,
        "context_chunks": collection.chunks,
        "fanout_plan": fanout_plan,
        "runner_guidance": {
            "process_chunks_in_waves_of": fanout_plan["batch_size"],
            "preserve_sources": True,
            "prefer_llm_query_batched_for_independent_chunk_work": True,
            "use_recursive_rlm_only_for_multi_step_subtasks": True,
        },
    }


def build_root_prompt(task_prompt: str, fanout_plan: dict[str, Any]) -> str:
    return (
        "Answer the task using the external REPL context. "
        "Do not answer from metadata alone; inspect context['context_chunks'] when chunks exist. "
        f"Process context chunks in waves of at most {fanout_plan['batch_size']} chunks. "
        "For independent extraction or summarization across chunks, use llm_query_batched on one wave at a time. "
        "Use rlm_query or rlm_query_batched only for subtasks that need their own multi-step reasoning loop. "
        f"Keep at most {fanout_plan['max_concurrent_recursive_subcalls']} recursive child RLM subcalls in flight. "
        "Preserve source_path and chunk id in intermediate summaries and cite sources when useful. "
        "When finished, store the answer in a variable named final_answer and call FINAL_VAR('final_answer').\n\n"
        f"Task: {task_prompt}"
    )


def package_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def build_backend_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"model_name": args.model}

    if args.base_url:
        if args.backend == "litellm":
            kwargs["api_base"] = args.base_url
        else:
            kwargs["base_url"] = args.base_url

    api_key = args.api_key
    if args.api_key_env:
        api_key = os.getenv(args.api_key_env)
        if not api_key:
            raise RunnerError(
                f"--api-key-env was set to {args.api_key_env}, but that environment variable is empty.",
                code="bad_arguments",
            )

    if api_key:
        kwargs["api_key"] = api_key
    elif args.backend == "vllm":
        # Local OpenAI-compatible servers usually require a syntactic key even when
        # they do not authenticate requests.
        kwargs["api_key"] = "EMPTY"

    return kwargs


def build_health(environment: str = "ipython") -> dict[str, Any]:
    python_supported = sys.version_info >= (3, 11)
    payload: dict[str, Any] = {
        "ok": True,
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "supported": python_supported,
        },
        "rlm": {
            "importable": False,
            "version": package_version("rlms") or package_version("rlm"),
            "error": None,
            "supported_environments": None,
            "requested_environment_supported": None,
            "effective_environment": environment,
        },
        "ipython": {
            "checked": environment == "ipython",
            "importable": None,
            "error": None,
        },
        "warnings": [],
        "install_guidance": INSTALL_GUIDANCE,
    }

    if not python_supported:
        payload["ok"] = False

    try:
        from rlm import RLM

        payload["rlm"]["importable"] = True
        environment_parameter = inspect.signature(RLM).parameters.get("environment")
        supported_environments = (
            sorted(supported_literal_values(environment_parameter.annotation))
            if environment_parameter is not None
            else []
        )
        if supported_environments:
            payload["rlm"]["supported_environments"] = supported_environments
            effective_environment, warning = resolve_runtime_environment(RLM, environment)
            payload["rlm"]["effective_environment"] = effective_environment
            payload["rlm"]["requested_environment_supported"] = effective_environment == environment
            if warning:
                payload["warnings"].append(warning)
            elif effective_environment == environment and environment not in supported_environments:
                payload["ok"] = False
                payload["rlm"]["error"] = f"Installed rlms does not support environment={environment}."
    except Exception as exc:
        payload["ok"] = False
        payload["rlm"]["error"] = str(exc)

    if environment == "ipython":
        try:
            import IPython  # noqa: F401
            import ipykernel  # noqa: F401

            payload["ipython"]["importable"] = True
        except Exception as exc:
            payload["ok"] = False
            payload["ipython"]["importable"] = False
            payload["ipython"]["error"] = str(exc)

    return payload


def require_runtime(environment: str) -> tuple[Any, Any, dict[str, Any]]:
    health = build_health(environment)
    if not health["ok"]:
        raise RunnerError("RLM runtime is not ready.", code="health_check_failed", details=health)

    from rlm import RLM
    from rlm.logger import RLMLogger

    return RLM, RLMLogger, health


def supported_literal_values(annotation: Any) -> set[str]:
    values = set()
    for value in get_args(annotation):
        if isinstance(value, str):
            values.add(value)
    return values


def supports_environment(RLM: Any, environment: str) -> bool:
    parameter = inspect.signature(RLM).parameters.get("environment")
    if parameter is None:
        return True

    supported = supported_literal_values(parameter.annotation)
    if not supported:
        return True
    return environment in supported


def resolve_runtime_environment(RLM: Any, requested_environment: str) -> tuple[str, str | None]:
    if supports_environment(RLM, requested_environment):
        return requested_environment, None

    if requested_environment == "ipython" and supports_environment(RLM, "local"):
        return (
            "local",
            "Installed rlms does not support environment=ipython; falling back to environment=local.",
        )

    return requested_environment, None


def environment_kwargs(args: argparse.Namespace, runtime_environment: str | None = None) -> dict[str, Any]:
    if (runtime_environment or args.environment) != "ipython":
        return {}
    return {
        "kernel_mode": args.kernel_mode,
        "cell_timeout": min(float(args.max_timeout), 60.0),
        "startup_timeout": 60,
        "subcall_timeout": float(args.max_timeout),
    }


def build_rlm_kwargs(
    RLM: Any,
    args: argparse.Namespace,
    *,
    runtime_environment: str,
    logger: Any,
) -> tuple[dict[str, Any], list[str]]:
    kwargs = {
        "backend": args.backend,
        "backend_kwargs": build_backend_kwargs(args),
        "environment": runtime_environment,
        "environment_kwargs": environment_kwargs(args, runtime_environment),
        "max_depth": args.max_depth,
        "max_iterations": args.max_iterations,
        "max_timeout": args.max_timeout,
        "max_errors": args.max_errors,
        "max_budget": args.max_budget,
        "logger": logger,
        "verbose": args.verbose,
    }
    optional_kwargs = {
        "max_concurrent_subcalls": args.max_concurrent_subcalls,
    }

    supported_parameters = inspect.signature(RLM).parameters
    warnings = []
    for name, value in optional_kwargs.items():
        if name in supported_parameters:
            kwargs[name] = value
        else:
            warnings.append(
                f"Installed rlms does not accept {name}; treating the configured subcall cap as advisory."
            )

    return kwargs, warnings


def add_runtime_compatibility_to_fanout_plan(
    RLM: Any,
    args: argparse.Namespace,
    fanout_plan: dict[str, Any],
) -> dict[str, Any]:
    updated = dict(fanout_plan)
    runtime_environment, environment_warning = resolve_runtime_environment(RLM, args.environment)
    warnings = [environment_warning] if environment_warning else []

    if runtime_environment != updated["environment"]:
        updated["requested_environment"] = updated["environment"]
        updated["environment"] = runtime_environment

    if "max_concurrent_subcalls" not in inspect.signature(RLM).parameters:
        warnings.append(
            "Installed rlms does not accept max_concurrent_subcalls; treating the configured subcall cap as advisory."
        )

    if warnings:
        existing_warnings = list(updated.get("warnings", []))
        for warning in warnings:
            if warning not in existing_warnings:
                existing_warnings.append(warning)
        updated["warnings"] = existing_warnings

    return updated


def run_live(args: argparse.Namespace, collection: ContextCollection, fanout_plan: dict[str, Any]) -> dict[str, Any]:
    RLM, RLMLogger, health = require_runtime(args.environment)
    logger = RLMLogger(log_dir=args.log_dir)
    fanout_plan = add_runtime_compatibility_to_fanout_plan(RLM, args, fanout_plan)
    runtime_environment = fanout_plan["environment"]

    rlm_kwargs, compatibility_warnings = build_rlm_kwargs(
        RLM,
        args,
        runtime_environment=runtime_environment,
        logger=logger,
    )
    runtime_warnings = [
        item
        for item in compatibility_warnings
        if item and item not in fanout_plan.get("warnings", [])
    ]
    if runtime_warnings:
        fanout_plan = dict(fanout_plan)
        fanout_plan["warnings"] = [*fanout_plan["warnings"], *runtime_warnings]

    rlm = RLM(**rlm_kwargs)

    context_payload = build_context_payload(
        task_prompt=args.prompt,
        collection=collection,
        fanout_plan=fanout_plan,
    )
    root_prompt = build_root_prompt(args.prompt, fanout_plan)

    started = time.perf_counter()
    try:
        result = rlm.completion(context_payload, root_prompt=root_prompt)
    finally:
        close = getattr(rlm, "close", None)
        if callable(close):
            close()

    usage_summary = None
    if getattr(result, "usage_summary", None) is not None:
        to_dict = getattr(result.usage_summary, "to_dict", None)
        usage_summary = to_dict() if callable(to_dict) else result.usage_summary

    return {
        "ok": True,
        "answer": result.response,
        "execution_time": getattr(result, "execution_time", time.perf_counter() - started),
        "usage_summary": usage_summary,
        "trajectory_log": logger.log_file_path,
        "fanout_plan": fanout_plan,
        "context_summary": context_summary(collection),
        "health": health,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = RunnerArgumentParser(description="Run RLM over files or directories for Codex.")
    parser.add_argument("--prompt", help="Question or task for RLM.")
    parser.add_argument("--context", action="append", default=[], help="Context file or directory. Repeatable.")
    parser.add_argument("--backend", default="openai")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL for local or proxy backends.")
    parser.add_argument("--api-key", help="API key passed to the backend. For local servers, use a dummy value.")
    parser.add_argument("--api-key-env", help="Read the backend API key from this environment variable.")
    parser.add_argument("--environment", default="ipython")
    parser.add_argument("--kernel-mode", default="subprocess", choices=["subprocess", "in_process"])
    parser.add_argument("--batch-size", type=positive_int, default=8)
    parser.add_argument("--max-concurrent-subcalls", type=positive_int, default=8)
    parser.add_argument("--max-depth", type=positive_int, default=2)
    parser.add_argument("--max-iterations", type=positive_int, default=12)
    parser.add_argument("--max-timeout", type=float, default=300.0)
    parser.add_argument("--max-errors", type=positive_int, default=4)
    parser.add_argument("--max-budget", type=float)
    parser.add_argument("--chunk-size", type=positive_int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=non_negative_int, default=DEFAULT_CHUNK_OVERLAP)
    parser.add_argument("--log-dir", default=".rlm/logs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.max_timeout <= 0:
        raise RunnerError("--max-timeout must be greater than 0", code="bad_arguments")
    if args.max_budget is not None and args.max_budget <= 0:
        raise RunnerError("--max-budget must be greater than 0", code="bad_arguments")
    if args.chunk_overlap >= args.chunk_size:
        raise RunnerError("--chunk-overlap must be smaller than --chunk-size", code="bad_arguments")
    if args.backend == "vllm" and not args.base_url:
        raise RunnerError("--base-url is required when --backend vllm is used", code="bad_arguments")
    if args.environment == "local":
        # This remains a warning in the output; live use is still allowed for trusted contexts.
        return


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        validate_args(args)

        if args.health:
            payload = build_health(args.environment)
            emit_json(payload)
            return 0 if payload["ok"] else 1

        if not args.prompt:
            raise RunnerError("--prompt is required unless --health is used", code="bad_arguments")

        collection = collect_context(
            args.context,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )

        warnings = list(collection.warnings)
        if not args.context:
            warnings.append("No --context paths supplied; RLM will receive only the task prompt.")
        if args.environment == "local":
            warnings.append("environment=local runs generated Python in the host process; use only for trusted context.")

        fanout_plan = build_fanout_plan(
            chunk_count=len(collection.chunks),
            batch_size=args.batch_size,
            max_concurrent_subcalls=args.max_concurrent_subcalls,
            environment=args.environment,
            model=args.model,
            warnings=warnings,
        )

        if args.dry_run:
            try:
                from rlm import RLM

                fanout_plan = add_runtime_compatibility_to_fanout_plan(RLM, args, fanout_plan)
            except Exception as exc:
                fanout_plan = dict(fanout_plan)
                fanout_plan["warnings"] = [
                    *fanout_plan["warnings"],
                    f"Runtime compatibility could not be checked during dry run: {exc}",
                ]
            emit_json(
                {
                    "ok": True,
                    "dry_run": True,
                    "fanout_plan": fanout_plan,
                    "context_summary": context_summary(collection),
                }
            )
            return 0

        payload = run_live(args, collection, fanout_plan)
        if args.json:
            emit_json(payload)
        else:
            print(payload["answer"])
        return 0

    except RunnerError as exc:
        fail_json(str(exc), code=exc.code, details=exc.details)
    except KeyboardInterrupt:
        fail_json("RLM run cancelled by user.", code="cancelled")
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        fail_json(str(exc), code=type(exc).__name__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
