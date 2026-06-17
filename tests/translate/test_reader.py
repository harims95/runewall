from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.translate.reader import read_url


HTML = """
<html>
  <head>
    <title>Example Page</title>
    <style>.hidden { display: none; }</style>
    <script>console.log("noise")</script>
  </head>
  <body>
    <nav>Navigation noise</nav>
    <main>
      <h1>Main Heading</h1>
      <h2>Section Heading</h2>
      <p>Hello world from Runewall.</p>
    </main>
    <footer>Footer noise</footer>
  </body>
</html>
"""


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class ReadUrlTests(unittest.TestCase):
    @patch("runewall.translate.reader._fetch_html", return_value=HTML)
    def test_read_url_returns_structured_content(self, mocked_fetch) -> None:
        content = read_url("https://example.com")

        mocked_fetch.assert_called_once_with("https://example.com")
        self.assertEqual(content["url"], "https://example.com")
        self.assertEqual(content["title"], "Example Page")
        self.assertEqual(content["headings"], ["Main Heading", "Section Heading"])
        self.assertIn("Hello world from Runewall.", content["text"])
        self.assertNotIn("Navigation noise", content["text"])
        self.assertNotIn("Footer noise", content["text"])


if __name__ == "__main__":
    unittest.main()
