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

    def test_execute_supabase_list_projects_blocked_by_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("supabase", "list_projects", {}, root=Path(temp_dir))

        self.assertEqual(
            str(context.exception),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_execute_supabase_list_projects_missing_token_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)

            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("supabase", "list_projects", {}, root=root)

        self.assertEqual(
            str(context.exception),
            "SUPABASE_ACCESS_TOKEN is required to execute supabase:list_projects.",
        )

    @patch.dict("os.environ", {"SUPABASE_ACCESS_TOKEN": "secret-supabase-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_get")
    def test_mocked_successful_supabase_response_returns_project_result(self, mocked_get) -> None:
        class Response:
            status_code = 200

            @staticmethod
            def json() -> list[dict[str, object]]:
                return [
                    {"id": "proj_1", "name": "my-db", "region": "us-east-1", "status": "ACTIVE_HEALTHY"},
                    {"id": "proj_2", "name": "staging-db", "region": "eu-west-1", "status": "ACTIVE_HEALTHY"},
                ]

        mocked_get.return_value = Response()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            result = execute_map_action("supabase", "list_projects", {}, root=root)

        self.assertEqual(result["project_count"], 2)
        self.assertEqual(len(result["projects"]), 2)
        self.assertEqual(result["projects"][0]["name"], "my-db")
        self.assertNotIn("secret-supabase-token", str(result))

    @patch.dict("os.environ", {"SUPABASE_ACCESS_TOKEN": "secret-supabase-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_get")
    def test_supabase_token_not_in_logged_result(self, mocked_get) -> None:
        class Response:
            status_code = 200

            @staticmethod
            def json() -> list[dict[str, object]]:
                return []

        mocked_get.return_value = Response()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            result = execute_map_action("supabase", "list_projects", {}, root=root)

        self.assertNotIn("secret-supabase-token", str(result))

    def test_execute_netlify_list_sites_blocked_by_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("netlify", "list_sites", {}, root=Path(temp_dir))

        self.assertEqual(
            str(context.exception),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_execute_netlify_list_sites_missing_token_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)

            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("netlify", "list_sites", {}, root=root)

        self.assertEqual(
            str(context.exception),
            "NETLIFY_TOKEN is required to execute netlify:list_sites.",
        )

    @patch.dict("os.environ", {"NETLIFY_TOKEN": "secret-netlify-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_get")
    def test_mocked_successful_netlify_response_returns_site_result(self, mocked_get) -> None:
        class Response:
            status_code = 200

            @staticmethod
            def json() -> list[dict[str, object]]:
                return [
                    {"id": "site_1", "name": "my-site", "url": "https://my-site.netlify.app", "admin_url": "https://app.netlify.com/sites/my-site"},
                    {"id": "site_2", "name": "api-site", "url": "https://api-site.netlify.app", "admin_url": "https://app.netlify.com/sites/api-site"},
                ]

        mocked_get.return_value = Response()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            result = execute_map_action("netlify", "list_sites", {}, root=root)

        self.assertEqual(result["site_count"], 2)
        self.assertEqual(len(result["sites"]), 2)
        self.assertEqual(result["sites"][0]["name"], "my-site")
        self.assertNotIn("secret-netlify-token", str(result))

    @patch.dict("os.environ", {"NETLIFY_TOKEN": "secret-netlify-token"}, clear=True)
    @patch("runewall.maps.executor._httpx_get")
    def test_netlify_token_not_in_logged_result(self, mocked_get) -> None:
        class Response:
            status_code = 200

            @staticmethod
            def json() -> list[dict[str, object]]:
                return []

        mocked_get.return_value = Response()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            result = execute_map_action("netlify", "list_sites", {}, root=root)

        self.assertNotIn("secret-netlify-token", str(result))

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


    def test_execution_disabled_has_error_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("github", "create_issue", {"repo": "u/r", "title": "t"}, root=Path(temp_dir))
        self.assertEqual(context.exception.error_code, "EXECUTION_DISABLED")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_vercel_token_has_missing_token_error_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("vercel", "list_projects", {}, root=root)
        self.assertEqual(context.exception.error_code, "MISSING_TOKEN")

    def test_unsupported_execution_has_unsupported_error_code(self) -> None:
        with self.assertRaises(UnsupportedExecutionError) as context:
            execute_map_action("slack", "send_message", {})
        self.assertEqual(context.exception.error_code, "UNSUPPORTED_EXECUTION")

    @patch.dict("os.environ", {"VERCEL_TOKEN": "tok"}, clear=True)
    @patch("runewall.maps.executor._httpx_get")
    def test_api_failure_has_api_error_code(self, mocked_get) -> None:
        class Response:
            status_code = 401
            def json(self) -> dict[str, str]:
                return {"message": "Unauthorized"}
            text = "Unauthorized"

        mocked_get.return_value = Response()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_allow_execute(root, True)
            with self.assertRaises(MapExecutionError) as context:
                execute_map_action("vercel", "list_projects", {}, root=root)
        self.assertEqual(context.exception.error_code, "API_ERROR")


if __name__ == "__main__":
    unittest.main()
