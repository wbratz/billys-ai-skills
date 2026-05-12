import importlib.util
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import Literal


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "rlm" / "scripts" / "rlm_run.py"
SPEC = importlib.util.spec_from_file_location("rlm_run", SCRIPT_PATH)
rlm_run = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = rlm_run
SPEC.loader.exec_module(rlm_run)


class RlmRunTests(unittest.TestCase):
    def test_estimate_batches(self):
        self.assertEqual(rlm_run.estimate_batches(0, 8), 0)
        self.assertEqual(rlm_run.estimate_batches(1, 8), 1)
        self.assertEqual(rlm_run.estimate_batches(8, 8), 1)
        self.assertEqual(rlm_run.estimate_batches(9, 8), 2)
        self.assertEqual(rlm_run.estimate_batches(17, 8), 3)

    def test_collect_context_ignores_directories_and_binary_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep").mkdir()
            (root / "keep" / "notes.txt").write_text("alpha beta gamma", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.txt").write_text("ignore me", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("ignore me", encoding="utf-8")
            (root / "binary.bin").write_bytes(b"\x00\x01\x02\x03")

            collection = rlm_run.collect_context(
                [str(root)],
                chunk_size=8,
                chunk_overlap=0,
            )

            paths = [Path(item["path"]).name for item in collection.files]
            self.assertEqual(paths, ["notes.txt"])
            self.assertEqual(len(collection.chunks), 2)
            self.assertEqual(collection.ignored_directory_count, 2)
            self.assertEqual(len(collection.skipped_files), 1)
            self.assertEqual(collection.skipped_files[0]["reason"], "binary file")

    def test_fanout_plan_reports_batch_and_concurrency(self):
        plan = rlm_run.build_fanout_plan(
            chunk_count=17,
            batch_size=8,
            max_concurrent_subcalls=8,
            environment="ipython",
            model="gpt-5.4",
            warnings=[],
        )

        self.assertEqual(plan["estimated_batches"], 3)
        self.assertEqual(plan["batch_size"], 8)
        self.assertEqual(plan["max_concurrent_recursive_subcalls"], 8)
        self.assertEqual(plan["environment"], "ipython")
        self.assertEqual(plan["model"], "gpt-5.4")

    def test_runtime_environment_falls_back_when_ipython_is_not_supported(self):
        class LegacyRLM:
            def __init__(
                self,
                *,
                environment: Literal["local", "docker"] = "local",
            ):
                self.environment = environment

        environment, warning = rlm_run.resolve_runtime_environment(LegacyRLM, "ipython")

        self.assertEqual(environment, "local")
        self.assertIn("environment=ipython", warning)
        self.assertIn("environment=local", warning)

    def test_build_rlm_kwargs_filters_unsupported_constructor_options(self):
        class LegacyRLM:
            def __init__(
                self,
                *,
                backend,
                backend_kwargs,
                environment: Literal["local", "docker"] = "local",
                environment_kwargs=None,
                max_depth=1,
                max_iterations=30,
                max_timeout=None,
                max_errors=None,
                max_budget=None,
                logger=None,
                verbose=False,
            ):
                pass

        args = Namespace(
            backend="openai",
            model="gpt-5.4",
            environment="ipython",
            kernel_mode="subprocess",
            max_depth=2,
            max_iterations=12,
            max_timeout=300,
            max_errors=4,
            max_budget=None,
            verbose=False,
            max_concurrent_subcalls=8,
            base_url=None,
            api_key=None,
            api_key_env=None,
        )

        kwargs, warnings = rlm_run.build_rlm_kwargs(
            LegacyRLM,
            args,
            runtime_environment="local",
            logger=object(),
        )

        self.assertEqual(kwargs["environment"], "local")
        self.assertEqual(kwargs["environment_kwargs"], {})
        self.assertNotIn("max_concurrent_subcalls", kwargs)
        self.assertTrue(any("max_concurrent_subcalls" in warning for warning in warnings))

    def test_build_backend_kwargs_supports_local_vllm_server(self):
        args = Namespace(
            backend="vllm",
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
            base_url="http://localhost:8000/v1",
            api_key=None,
            api_key_env=None,
        )

        kwargs = rlm_run.build_backend_kwargs(args)

        self.assertEqual(kwargs["model_name"], "Qwen/Qwen2.5-Coder-7B-Instruct")
        self.assertEqual(kwargs["base_url"], "http://localhost:8000/v1")
        self.assertEqual(kwargs["api_key"], "EMPTY")

    def test_build_backend_kwargs_reads_api_key_env(self):
        args = Namespace(
            backend="openai",
            model="gpt-5.4",
            base_url=None,
            api_key=None,
            api_key_env="RLM_TEST_API_KEY",
        )

        previous = rlm_run.os.environ.get("RLM_TEST_API_KEY")
        try:
            rlm_run.os.environ["RLM_TEST_API_KEY"] = "test-key"
            kwargs = rlm_run.build_backend_kwargs(args)
        finally:
            if previous is None:
                rlm_run.os.environ.pop("RLM_TEST_API_KEY", None)
            else:
                rlm_run.os.environ["RLM_TEST_API_KEY"] = previous

        self.assertEqual(kwargs["api_key"], "test-key")

    def test_fanout_plan_includes_runtime_compatibility_warnings(self):
        class LegacyRLM:
            def __init__(
                self,
                *,
                environment: Literal["local", "docker"] = "local",
            ):
                pass

        args = Namespace(environment="ipython", max_concurrent_subcalls=8)
        plan = {
            "batch_size": 8,
            "chunk_count": 1,
            "estimated_batches": 1,
            "max_concurrent_recursive_subcalls": 8,
            "environment": "ipython",
            "model": "gpt-5.4",
            "warnings": [],
        }

        updated = rlm_run.add_runtime_compatibility_to_fanout_plan(LegacyRLM, args, plan)

        self.assertEqual(updated["requested_environment"], "ipython")
        self.assertEqual(updated["environment"], "local")
        self.assertTrue(any("environment=ipython" in warning for warning in updated["warnings"]))
        self.assertTrue(any("max_concurrent_subcalls" in warning for warning in updated["warnings"]))


if __name__ == "__main__":
    unittest.main()
