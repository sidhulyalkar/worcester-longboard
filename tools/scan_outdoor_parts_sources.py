#!/usr/bin/env python3
"""Opt-in, robots-aware, bounded official-source metadata scanner.

Does not scrape seller checkout pages, publish prices, infer SKUs, or modify
the canonical catalog. A source refresh is a NEW untrusted review candidate.
Usage:
  python tools/scan_outdoor_parts_sources.py --out /tmp/source-plan.json
  python tools/scan_outdoor_parts_sources.py --fetch --limit 3 --out /tmp/source-check.json

Network access is disabled by default; --fetch is explicitly opt-in.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog/outdoor_parts_picker.v1.json"
AGENT = "WorcesterPartsResearch/0.1 (+https://github.com/sidhulyalkar/worcester-longboard)"
MAX_HTML_BYTES = 512 * 1024
MAX_ROBOTS_BYTES = 64 * 1024
TIMEOUT_SECONDS = 8.0
MIN_HOST_DELAY_SECONDS = 2.0


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self._title = False
        self.title = ""
        self.description = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._title = True
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content", "")[:500]

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False

    def handle_data(self, data):
        if self._title:
            self.title = (self.title + data)[:250]


def safe_https_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and not parsed.username
        and not parsed.password
        and not parsed.fragment
        and parsed.port in (None, 443)
        and (parsed.hostname.endswith(".com") or parsed.hostname.endswith(".org"))
        and not (parsed.hostname or "").startswith("localhost")
    )


def robot_permission(robots_content: str, page_url: str) -> bool:
    parser = RobotFileParser()
    parser.set_url(f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}/robots.txt")
    parser.parse(robots_content.splitlines())
    # An empty, unavailable or ambiguous robots file must not grant access.
    return bool(robots_content.strip()) and parser.can_fetch(AGENT, page_url)


def _bounded_read(response, limit: int) -> bytes:
    data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("response exceeds bounded scan limit")
    return data


def fetch_page(url: str, timeout: float = TIMEOUT_SECONDS, limit: int = MAX_HTML_BYTES):
    assert safe_https_url(url), "unsafe manufacturer URL"
    original = urlparse(url).hostname
    req = Request(url, headers={"User-Agent": AGENT, "Accept": "text/html"})
    with urlopen(req, timeout=timeout) as response:
        final_url = response.geturl()
        if not safe_https_url(final_url) or urlparse(final_url).hostname != original:
            raise ValueError("redirected off original maker host; manual review required")
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("not an HTML manufacturer page")
        data = _bounded_read(response, limit)
        metadata = Metadata()
        metadata.feed(data.decode("utf-8", errors="replace"))
        return {
            "status": "UNTRUSTED_HTML_METADATA_FOR_REVIEW",
            "final_url": final_url,
            "title": metadata.title.strip(),
            "description_excerpt": metadata.description,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes_hashed": len(data),
            "content_type": content_type,
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "variant_and_stock_verified": False,
            "published_to_catalog": False,
        }


def scan_sources(registry: dict, do_fetch=False, limit=None, delay=MIN_HOST_DELAY_SECONDS):
    sources = registry["sources"][:limit] if limit else registry["sources"]
    result = []
    robots = {}
    last_access = {}
    for row in sources:
        url = row["url"]
        item = {"source_id": row["id"], "source_url": url,
                "manufacturer_reviewed_on": row["reviewed_on"],
                "scan_state": "NOT_FETCHED_REVIEW_REQUIRED",
                "supplier_order_unit_verified": False,
                "live_stock_verified": False,
                "physical_qualification_authorized": False}
        if not safe_https_url(url):
            item["scan_state"] = "UNSAFE_URL_HOLD"
        elif do_fetch:
            host = urlparse(url).netloc
            if host not in robots:
                robot_url = "https://" + host + "/robots.txt"
                try:
                    with urlopen(Request(robot_url, headers={"User-Agent": AGENT}),
                                 timeout=TIMEOUT_SECONDS) as response:
                        robots[host] = _bounded_read(response, MAX_ROBOTS_BYTES).decode(
                            "utf-8", errors="replace")
                except Exception:
                    robots[host] = ""
            if not robot_permission(robots[host], url):
                item["scan_state"] = "ROBOTS_UNAVAILABLE_OR_DISALLOWED_HOLD"
            else:
                gap = time.monotonic() - last_access.get(host, 0)
                if host in last_access and gap < delay:
                    time.sleep(delay - gap)
                last_access[host] = time.monotonic()
                try:
                    item.update(fetch_page(url))
                    item["scan_state"] = item.pop("status")
                    item["scanned_at_utc"] = datetime.now(timezone.utc).isoformat()
                except Exception as e:
                    item["scan_state"] = "NETWORK_OR_SOURCE_REVIEW_HOLD"
                    item["error_kind"] = type(e).__name__
        result.append(item)
    return {
        "schema_version": 1,
        "scope": "UNTRUSTED_SOURCE_REFRESH_CANDIDATES_NOT_CATALOG_UPDATES",
        "fetch_enabled": do_fetch,
        "requested_source_count": len(sources),
        "rows": result,
        "approved_for_sourcing": False,
        "note": "Metadata only. Human manufacturer evidence review is required to revise actual product/variant/pack claims."
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--fetch", action="store_true",
                    help="Explicit opt-in to robots-aware manufacturer-page fetches")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--delay", type=float, default=MIN_HOST_DELAY_SECONDS)
    args = ap.parse_args()
    if args.limit is not None and args.limit < 1:
        ap.error("--limit must be positive")
    if args.delay < MIN_HOST_DELAY_SECONDS:
        ap.error("delay must be >= 2 seconds per host")
    data = json.loads(args.registry.read_text())
    if data.get("scope") != "EVIDENCE_AWARE_OUTDOOR_PARTS_RESEARCH_NO_CHECKOUT":
        ap.error("registry has an unsupported authority scope")
    report = scan_sources(data, do_fetch=args.fetch, limit=args.limit, delay=args.delay)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
