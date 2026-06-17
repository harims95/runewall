from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import EMPTY_LOG_MESSAGE, main


class CliTests(unittest.TestCase):
    def test_init_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["init"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / ".runewall" / "runewall.db").exists())
            self.assertIn("Initialized Runewall at", output.getvalue())

    def test_log_command_with_empty_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["log"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), EMPTY_LOG_MESSAGE)


if __name__ == "__main__":
    unittest.main()
