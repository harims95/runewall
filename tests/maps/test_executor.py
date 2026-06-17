from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.maps.executor import MapExecutionError, UnsupportedExecutionError, execute_map_action


class MapExecutorTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_execute_github_create_issue_with_missing_token_fails_clearly(self) -> None:
        with self.assertRaises(MapExecutionError) as context:
            execute_map_action("github", "create_issue", {"repo": "user/repo", "title": "Bug report"})

        self.assertEqual(
            str(context.exception),
            "GITHUB_TOKEN is required to execute github:create_issue.",
        )

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_post")
    def test_mocked_successful_github_response_returns_issue_result(self, mocked_post) -> None:
        class Response:
            status_code = 201

            @staticmethod
            def json() -> dict[str, object]:
                return {"html_url": "https://github.com/user/repo/issues/1", "number": 1}

        mocked_post.return_value = Response()

        result = execute_map_action(
            "github",
            "create_issue",
            {"repo": "user/repo", "title": "Bug report", "body": "Details"},
        )

        self.assertEqual(
            result,
            {"issue_url": "https://github.com/user/repo/issues/1", "issue_number": 1},
        )
        _, kwargs = mocked_post.call_args
        self.assertEqual(kwargs["json"], {"title": "Bug report", "body": "Details"})
        self.assertNotIn("secret-token", str(kwargs["json"]))

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    def test_unsupported_site_flow_execution_fails_clearly(self) -> None:
        with self.assertRaises(UnsupportedExecutionError) as context:
            execute_map_action("github", "delete_repository", {"repo": "user/repo"})

        self.assertEqual(
            str(context.exception),
            "Execution is not supported for github:delete_repository.",
        )


if __name__ == "__main__":
    unittest.main()
