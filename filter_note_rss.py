#!/usr/bin/env python3
"""Create a minimal RSS feed from a note.com RSS feed.

The output feed keeps only the newest item and includes its title and URL.
"""

from __future__ import annotations

import argparse
from email.utils import parsedate_to_datetime
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from datetime import timezone
from email.utils import format_datetime, parsedate_to_datetime

def rss_date_gmt(value: str) -> str:
    dt = parsedate_to_datetime(value)
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)

def read_input(source: str) -> bytes:
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
    child = element.find(name)
    return child.text if child is not None and child.text else ""


def set_child(parent: ET.Element, name: str, value: str) -> None:
    child = ET.SubElement(parent, name)
    child.text = value


def item_date(item: ET.Element):
    pub_date = child_text(item, "pubDate")
    if not pub_date:
        return None
    try:
        return parsedate_to_datetime(pub_date)
    except (TypeError, ValueError):
        return None


def newest_item(items: list[ET.Element]) -> ET.Element:
    dated_items = [(item_date(item), index, item) for index, item in enumerate(items)]
    dated_items_with_date = [entry for entry in dated_items if entry[0] is not None]
    if not dated_items_with_date:
        return items[0]

    return max(dated_items_with_date, key=lambda entry: (entry[0], -entry[1]))[2]


def build_short_feed(feed_bytes: bytes) -> ET.ElementTree:
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

    for name in ("title", "link"):
        set_child(channel, name, child_text(source_channel, name))

    set_child(channel, "description", "最新1件の記事タイトルとURL")

    item = ET.SubElement(channel, "item")
    
    title = child_text(source_item, "title")
    link = child_text(source_item, "link")
    pub_date = child_text(source_item, "pubDate")
        
    if title:
        set_child(item, "title", title)
    
    if link:
        set_child(item, "link", link)
    
    if link:
        guid = ET.SubElement(item, "guid", {"isPermaLink": "true"})
        guid.text = link
  
    if pub_date:
        safe_pub_date = rss_date_gmt(pub_date)
        set_child(channel, "lastBuildDate", safe_pub_date)
        set_child(item, "pubDate", safe_pub_date)
   
    description = title
    if link:
        description = f"{title}\n{link}" if title else link
    
    if description:
        set_child(item, "description", description)

    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a note.com RSS feed and write a feed with only the newest item's title and URL."
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
