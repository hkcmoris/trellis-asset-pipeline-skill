from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from trellis_pipeline.quiet import run_quiet, tail_log


class QuietRunTests(unittest.TestCase):
    def test_captures_child_output_in_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "job.log"

            result = run_quiet(
                [
                    sys.executable,
                    "-c",
                    "print('quarter complete'); print('finished')",
                ],
                log_path=log,
            )

            self.assertEqual(result.returncode, 0)
            self.assertTrue(log.is_file())
            self.assertIn("quarter complete", log.read_text(encoding="utf-8"))
            self.assertIn("finished", tail_log(log))

    def test_returns_nonzero_exit_code_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "job.log"

            result = run_quiet(
                [
                    sys.executable,
                    "-c",
                    "print('failure detail'); raise SystemExit(7)",
                ],
                log_path=log,
            )

            self.assertEqual(result.returncode, 7)
            self.assertIn("failure detail", tail_log(log))


if __name__ == "__main__":
    unittest.main()
