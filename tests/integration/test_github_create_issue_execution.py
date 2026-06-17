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
from runewall.core.log import ActionLog


class GitHubCreateIssueExecutionIntegrationTests(unittest.TestCase):
    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_post")
    def test_mocked_successful_github_response_logs_map_execute_success(self, mocked_post) -> None:
        class Response:
            status_code = 201

            @staticmethod
            def json() -> dict[str, object]:
                return {
                    "html_url": "https://github.com/user/repo/issues/12",
                    "number": 12,
                }

        mocked_post.return_value = Response()

        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                            "--input",
                            "body=Details",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.execute")
        self.assertEqual(action.target, "github:create_issue")
        self.assertEqual(action.status, "success")
        self.assertEqual(
            action.result,
            {"issue_url": "https://github.com/user/repo/issues/12", "issue_number": 12},
        )
        self.assertNotIn("secret-token", str(action.params))
        self.assertNotIn("secret-token", str(action.result))
        self.assertIn("Issue number: 12", output.getvalue())


if __name__ == "__main__":
    unittest.main()
