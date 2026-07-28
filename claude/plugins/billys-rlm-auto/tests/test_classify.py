#!/usr/bin/env python3
"""
Tests for the rlm-auto classifier.

Run with:
  py -3 tests/test_classify.py
or:
  py -3 -m unittest tests.test_classify

These cover the contract the classifier is supposed to honor:
- Strong positive: a real big directory + corpus verbs -> verdict=rlm
- Strong negative: small edit verbs -> verdict=direct
- Path categorization on Windows (backslash AND forward-slash variants)
- Ambiguous band when keywords hit but no path stat backs them up
- Negative keywords subtract from positives
- Kill switch via env var
- Glob patterns add signal
- Multiple URLs lean toward RLM
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Make scripts/ importable
THIS = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS.parent / "scripts"))

from classify import classify  # noqa: E402


def _make_big_dir(root: Path, n_files: int = 30, file_size: int = 3000) -> Path:
    d = root / "big_dir"
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n_files):
        (d / f"f{i}.txt").write_text("x" * file_size)
    return d


def _make_small_file(root: Path) -> Path:
    p = root / "small.txt"
    p.write_text("hello")
    return p


class ClassifierTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Make sure env kill switch is unset for these tests
        os.environ.pop("RLM_AUTO_DISABLE", None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # ---- Strong positive cases ----

    def test_big_dir_plus_corpus_verb_is_rlm(self):
        d = _make_big_dir(self.root)
        result = classify(f"audit every file in {d} for security issues", cwd=str(self.root))
        self.assertEqual(result["verdict"], "rlm", msg=str(result))
        self.assertGreaterEqual(result["score"], 0.6)
        self.assertTrue(any(s["kind"] == "dir" for s in result["signals"]))

    def test_big_dir_forward_slash_windows_style(self):
        d = _make_big_dir(self.root)
        # Use forward slashes even when running on Windows
        forward = str(d).replace("\\", "/")
        result = classify(f"summarize all files under {forward}", cwd=str(self.root))
        self.assertEqual(result["verdict"], "rlm", msg=str(result))

    def test_many_urls_lean_rlm(self):
        result = classify(
            "compare these papers: https://a.com/x https://b.com/y https://c.com/z https://d.com/w",
            cwd=str(self.root),
        )
        self.assertIn(result["verdict"], ("rlm", "ambiguous"))
        self.assertEqual(result["totals"]["url_count"], 4)
        self.assertTrue(any(s["kind"] == "many_urls" for s in result["signals"]))

    # ---- Strong negative cases ----

    def test_small_edit_is_direct(self):
        result = classify("rename the foo function to bar in auth.py", cwd=str(self.root))
        self.assertEqual(result["verdict"], "direct", msg=str(result))
        self.assertEqual(result["score"], 0.0)

    def test_single_file_question_is_direct(self):
        result = classify("explain this function in auth.py", cwd=str(self.root))
        self.assertEqual(result["verdict"], "direct", msg=str(result))

    def test_negative_keyword_subtracts(self):
        # Positive keyword "every" alone would push into ambiguous; negative
        # keyword "this file" pulls it back to direct.
        d = _make_big_dir(self.root)
        positive_only = classify(
            f"summarize every file in {d}", cwd=str(self.root)
        )
        with_negative = classify(
            f"summarize every line in this file at {d}/f0.txt",
            cwd=str(self.root),
        )
        self.assertGreater(positive_only["score"], with_negative["score"])

    # ---- Ambiguous band ----

    def test_keywords_without_path_is_ambiguous_or_direct(self):
        # Imaginary paths shouldn't push into RLM since size data is missing.
        result = classify(
            "summarize every PDF under ./does_not_exist/ for the Q3 review",
            cwd=str(self.root),
        )
        self.assertIn(result["verdict"], ("ambiguous", "direct"), msg=str(result))

    # ---- Path categorization ----

    def test_small_existing_file_does_not_force_rlm(self):
        p = _make_small_file(self.root)
        result = classify(f"explain {p}", cwd=str(self.root))
        # Small file with no corpus verbs -> direct
        self.assertEqual(result["verdict"], "direct", msg=str(result))

    def test_windows_backslash_path_is_categorized(self):
        d = _make_big_dir(self.root)
        # Build a Windows-style path string using backslashes
        win_style = str(d).replace("/", "\\")
        result = classify(f"audit all files in {win_style}", cwd=str(self.root))
        # Must successfully find the dir (size>0)
        self.assertGreater(result["totals"]["size_bytes"], 0, msg=str(result))

    def test_relative_backslash_path_is_categorized(self):
        d = _make_big_dir(self.root)
        relative = str(d.relative_to(self.root)).replace("/", "\\")
        result = classify(
            f"audit all files in .\\{relative}",
            cwd=str(self.root),
        )
        self.assertGreater(result["totals"]["size_bytes"], 0, msg=str(result))

    # ---- Globs ----

    def test_glob_pattern_adds_signal(self):
        result = classify("review every change in src/**/*.py", cwd=str(self.root))
        self.assertTrue(any(s["kind"] == "glob" for s in result["signals"]),
                        msg=str(result))

    # ---- Config / kill switch ----

    def test_kill_switch_env_disables(self):
        os.environ["RLM_AUTO_DISABLE"] = "1"
        try:
            d = _make_big_dir(self.root)
            result = classify(f"audit every file in {d}", cwd=str(self.root))
            self.assertEqual(result["verdict"], "direct")
            self.assertTrue(any(s["kind"] == "disabled" for s in result["signals"]))
        finally:
            os.environ.pop("RLM_AUTO_DISABLE", None)

    # ---- Output shape contract ----

    def test_output_shape(self):
        result = classify("hello world", cwd=str(self.root))
        for key in ("verdict", "score", "signals", "totals", "config_used"):
            self.assertIn(key, result)
        self.assertIn(result["verdict"], ("rlm", "ambiguous", "direct"))
        self.assertIsInstance(result["score"], float)
        self.assertIsInstance(result["signals"], list)
        for k in ("size_bytes", "file_count", "url_count"):
            self.assertIn(k, result["totals"])

    def test_score_bounded_0_1(self):
        # Pile on positive signals; score should still clamp at 1.0
        d = _make_big_dir(self.root, n_files=200, file_size=10_000)
        prompt = (
            f"audit every file under {d}, sweep across all logs, compare across "
            f"every PDF, exhaustively review the entire corpus"
        )
        result = classify(prompt, cwd=str(self.root))
        self.assertLessEqual(result["score"], 1.0)
        self.assertGreaterEqual(result["score"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
