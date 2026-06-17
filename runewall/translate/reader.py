from __future__ import annotations

from typing import TypedDict


class ReadResult(TypedDict):
    url: str
    title: str
    headings: list[str]
    text: str


def read_url(url: str) -> ReadResult:
    html = _fetch_html(url)
    soup = _parse_html(html)
    for tag_name in ("script", "style", "nav", "footer"):
        for tag in soup.find_all(tag_name):
            tag.decompose()

    title_tag = soup.find("title")
    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.find_all(["h1", "h2", "h3"])
        if heading.get_text(" ", strip=True)
    ]
    text = " ".join(soup.stripped_strings)

    return {
        "url": url,
        "title": title_tag.get_text(" ", strip=True) if title_tag else "",
        "headings": headings,
        "text": text,
    }


def _fetch_html(url: str) -> str:
    import httpx

    response = httpx.get(url, follow_redirects=True, timeout=10.0)
    response.raise_for_status()
    return response.text


def _parse_html(html: str):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")
