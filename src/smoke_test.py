"""
Smoke Test Suite for Phase 0.
Validates:
1. Import integrity and project root derivation.
2. Directory structure presence.
3. Path containment (no hardcoded paths outside project root).
4. PoliteFetcher caching, checksum verification, and robots checking.
5. Report generation and non-emptiness.
"""

import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_DIR))

from src import config
from src.utils.fetcher import PoliteFetcher, FetchResult, RobotsDisallowedError


class Phase0SmokeTest(unittest.TestCase):

    def test_01_paths_containment(self):
        """Verify all defined paths are within project root."""
        root = config.PROJECT_ROOT.resolve()
        self.assertTrue(root.exists(), f"Project root does not exist: {root}")

        subdirs = [
            config.SRC_DIR,
            config.DATA_DIR,
            config.DATA_RAW_DIR,
            config.DATA_CLEANED_DIR,
            config.DATA_MODEL_DIR,
            config.REPORTS_DIR,
            config.LOGS_DIR,
            config.CACHE_DIR,
        ]
        for d in subdirs:
            resolved_d = d.resolve()
            self.assertTrue(
                str(resolved_d).startswith(str(root)),
                f"Path {resolved_d} is outside project root {root}!",
            )
            self.assertTrue(resolved_d.exists(), f"Directory {resolved_d} does not exist!")

    def test_02_target_seasons(self):
        """Verify 8 target seasons from 2018/19 through 2025/26 are configured."""
        seasons = config.TARGET_SEASONS
        self.assertEqual(len(seasons), 8, f"Expected 8 seasons, found {len(seasons)}")
        self.assertEqual(seasons[0]["canonical"], "2018-19")
        self.assertEqual(seasons[-1]["canonical"], "2025-26")

    def test_03_fetcher_cache_roundtrip(self):
        """Verify PoliteFetcher saves and loads from cache with SHA-256 validation."""
        fetcher = PoliteFetcher(cache_dir=config.CACHE_DIR)
        test_url = "https://example.com/smoke-test-fixture"
        test_content = b"Premier League Smoke Test Cache Content 2026"

        # Directly save to cache
        sha = fetcher._save_to_cache(
            url=test_url,
            final_url=test_url,
            status_code=200,
            content=test_content,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            content_type="text/plain; charset=utf-8",
            fetched_at_utc="2026-10-24T00:00:00Z",
        )
        self.assertIsNotNone(sha)

        # Load from cache
        cached_result = fetcher._load_from_cache(test_url)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.content, test_content)
        self.assertEqual(cached_result.sha256, sha)
        self.assertTrue(cached_result.from_cache)

        # Clean up test fixture files
        content_path, meta_path = fetcher._get_cache_paths(test_url)
        if content_path.exists():
            content_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    def test_04_robots_understat_disallow(self):
        """Verify robots parser correctly detects Understat Disallow: /."""
        fetcher = PoliteFetcher()
        # Understat disallows all
        allowed = fetcher.is_allowed_by_robots("https://understat.com/league/EPL")
        self.assertFalse(allowed, "Understat should be disallowed by robots.txt!")

    def test_05_report_exists(self):
        """Verify reports/phase_00_sources.md exists and contains verified sources."""
        report_path = config.REPORTS_DIR / "phase_00_sources.md"
        self.assertTrue(report_path.exists(), f"Report file missing: {report_path}")
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("Football-Data", content)
        self.assertIn("11v11", content)
        self.assertIn("Wikipedia", content)
        self.assertIn("Understat", content)
        self.assertTrue("Điều gì đã xác minh" in content or "đã xác minh" in content.lower())
        self.assertTrue("Điều gì chưa xác minh" in content or "chưa xác minh" in content.lower())


def run_tests() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(Phase0SmokeTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
