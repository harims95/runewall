from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.maps.executor import MapExecutionError, UnsupportedExecutionError, execute_map_action


class MapExecutorTests(unittest.TestCase):
    def _write_allow_execute(self, root: Path, enabled: bool) -> None:
        config_dir = root / ".runewall"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.toml").write_text(
            f"[maps]\nallow_execute = {'true' if enabled else 'false'}\n",
            encoding="utf-8",
        )

    def test_execute_is_blocked_when_config_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(MapExecutionError) as context:
                execute_map_action(
                    "github",
                    "create_issue",
                    {"repo": "user/repo", "title": "Bug report"},
                    root=Path(temp_dir),
                )

        self.assertEqual(
            str(context.exception),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_execute_github_create_issue_with_missing_token_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)

            with self.assertRaises(MapExecutionError) as context:
                execute_map_action(
                    "github",
                    "create_issue",
                    {"repo": "user/repo", "title": "Bug report"},
                    root=root,
                )

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

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            result = execute_map_action(
                "github",
                "create_issue",
                {"repo": "user/repo", "title": "Bug report", "body": "Details"},
                root=root,
            )

        self.assertEqual(
            result,
            {"issue_url": "https://github.com/user/repo/issues/1", "issue_number": 1},
        )
        _, kwargs = mocked_post.call_args
        self.assertEqual(kwargs["json"], {"title": "Bug report", "body": "Details"})
        self.assertNotIn("secret-token", str(kwargs["json"]))

    def test_execute_vercel_list_projects_blocked_by_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("vercel", "list_projects", {}, root=Path(temp_dir))

        self.assertEqual(
            str(context.exception),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_execute_vercel_list_projects_missing_token_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)

            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("vercel", "list_projects", {}, root=root)

        self.assertEqual(
            str(context.exception),
            "VERCEL_TOKEN is required to execute vercel:list_projects.",
        )

    @patch.dict("os.environ", {"VERCEL_TOKEN": "secret-vercel-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_get")
    def test_mocked_successful_vercel_response_returns_project_result(self, mocked_get) -> None:
        class Response:
            status_code = 200

            @staticmethod
            def json() -> dict[str, object]:
                return {
                    "projects": [
                        {"id": "proj_1", "name": "my-app", "framework": "nextjs"},
                        {"id": "proj_2", "name": "api", "framework": None},
                    ]
                }

        mocked_get.return_value = Response()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            result = execute_map_action("vercel", "list_projects", {}, root=root)

        self.assertEqual(result["project_count"], 2)
        self.assertEqual(len(result["projects"]), 2)
        self.assertEqual(result["projects"][0]["name"], "my-app")
        args, kwargs = mocked_get.call_args
        self.assertNotIn("secret-vercel-token", str(kwargs.get("json", {})))

    @patch.dict("os.environ", {"VERCEL_TOKEN": "secret-vercel-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_get")
    def test_vercel_token_not_in_logged_result(self, mocked_get) -> None:
        class Response:
            status_code = 200

            @staticmethod
            def json() -> dict[str, object]:
                return {"projects": []}

        mocked_get.return_value = Response()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            result = execute_map_action("vercel", "list_projects", {}, root=root)

        self.assertNotIn("secret-vercel-token", str(result))

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    def test_unsupported_site_flow_execution_fails_clearly(self) -> None:
        with self.assertRaises(UnsupportedExecutionError) as context:
            execute_map_action("github", "delete_repository", {"repo": "user/repo"}, root=Path.cwd())

        self.assertEqual(
            str(context.exception),
            "Execution is not supported for github:delete_repository.",
        )


if __name__ == "__main__":
    unittest.main()
