#!/usr/bin/env python3
"""Create a minimal RSS feed from a note.com RSS feed.

The output feed keeps only the newest item and includes:
- channel title
- channel link
- channel description
- channel lastBuildDate converted to GMT
- newest item title
- newest item URL

This intentionally avoids item guid, item pubDate, and item description
for compatibility with simple RSS readers such as quote/0.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError


def rss_date_gmt(value: str) -> str:
    """Convert RSS date string to GMT format."""
    dt = parsedate_to_datetime(value)
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def read_input(source: str) -> bytes:
    """Read RSS from URL or local file."""
    if source.startswith(("http://", "https://")):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        }

        last_error: Exception | None = None

        for attempt in range(3):
            try:
                request = urllib.request.Request(source, headers=headers)
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.read()
            except HTTPError as exc:
                last_error = exc
                print(
                    f"warning: HTTP error {exc.code}: {exc.reason} "
                    f"(attempt {attempt + 1}/3)",
                    file=sys.stderr,
                )
                time.sleep(10)
            except URLError as exc:
                last_error = exc
                print(
                    f"warning: URL error: {exc.reason} "
                    f"(attempt {attempt + 1}/3)",
                    file=sys.stderr,
                )
                time.sleep(10)

        if last_error is not None:
            raise last_error

    return Path(source).read_bytes()


def child_text(element: ET.Element, name: str) -> str:
    """Get child element text."""
    child = element.find(name)
    return child.text.strip() if child is not None and child.text else ""


def set_child(parent: ET.Element, name: str, value: str) -> None:
    """Add child element with text."""
    child = ET.SubElement(parent, name)
    child.text = value


def item_date(item: ET.Element):
    """Get item pubDate as datetime, if possible."""
    pub_date = child_text(item, "pubDate")
    if not pub_date:
        return None

    try:
        return parsedate_to_datetime(pub_date)
    except (TypeError, ValueError):
        return None


def newest_item(items: list[ET.Element]) -> ET.Element:
    """Return newest item by pubDate. If no dates exist, return first item."""
    dated_items = [(item_date(item), index, item) for index, item in enumerate(items)]
    dated_items_with_date = [entry for entry in dated_items if entry[0] is not None]

    if not dated_items_with_date:
        return items[0]

    return max(dated_items_with_date, key=lambda entry: (entry[0], -entry[1]))[2]


def build_short_feed(feed_bytes: bytes) -> ET.ElementTree:
    """Build minimal RSS feed for quote/0."""
    source_root = ET.fromstring(feed_bytes)
    source_channel = source_root.find("channel")

    if source_channel is None:
        raise ValueError("RSS 2.0 feed with <channel> is required")

    items = source_channel.findall("item")

    if not items:
        raise ValueError("RSS feed has no <item>")

    source_item = newest_item(items)

    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")

    source_title = child_text(source_channel, "title")
    source_link = child_text(source_channel, "link")

    if source_title:
        set_child(channel, "title", source_title)

    if source_link:
        set_child(channel, "link", source_link)

    set_child(channel, "description", "最新1件の記事タイトルとURL")

    # Prefer source channel lastBuildDate.
    # If it does not exist, fall back to newest item's pubDate.
    source_last_build_date = child_text(source_channel, "lastBuildDate")
    source_pub_date = child_text(source_item, "pubDate")

    date_source = source_last_build_date or source_pub_date

    if date_source:
        safe_date = rss_date_gmt(date_source)
        set_child(channel, "lastBuildDate", safe_date)

    item = ET.SubElement(channel, "item")

    title = child_text(source_item, "title")
    link = child_text(source_item, "link")

    if title:
        set_child(item, "title", title)

    if link:
        set_child(item, "link", link)

    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch a note.com RSS feed and write a minimal feed "
            "with only the newest item's title and URL."
        )
    )
    parser.add_argument("source", help="RSS URL or local RSS/XML file path")
    parser.add_argument("output", help="Output RSS file path")
    args = parser.parse_args()

    try:
        feed = build_short_feed(read_input(args.source))
        feed.write(args.output, encoding="utf-8", xml_declaration=True)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
