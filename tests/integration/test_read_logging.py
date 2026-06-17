from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import main
from runewall.core.db import database_path
from runewall.core.log import ActionLog


class ReadLoggingIntegrationTests(unittest.TestCase):
    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": ["Main Heading"],
            "text": "Hello world from Runewall.",
        },
    )
    def test_read_without_init_works_but_does_not_log(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            mocked_read.assert_called_once_with("https://example.com")
            self.assertFalse(database_path(Path(temp_dir)).exists())
            self.assertIn("Runewall is not initialized; read action was not logged.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
