#!/usr/bin/env python3
"""Crawl every URL found in this SDK repo (and optionally the website repo).

Usage:
    python3 scripts/link_crawl.py [--website PATH_TO_WEBSITE_CLONE] [--list]

Pass: final status 200 reached directly or through permanent redirects (301/308).
Warn: temporary redirect (302/307) to a 200, e.g. a login wall.
Blocked: a site that refuses automated requests (LinkedIn, X); check by hand.
Fail: anything else. Exit 1 if any URL fails.

Skipped (and listed as SKIP): localhost, placeholders (RECEIPT_ID, {id}, $VAR),
POST-only API endpoints, XML namespaces, preconnect origins.
Standard library only; one GET per URL, sequential.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://inquiroresearchlabs.ai"
URL_RE = re.compile(r"""https?://[^\s"'<>)\]`|\\]+""")
HREF_RE = re.compile(r"""(?:href|src)\s*=\s*["'](/[^"'#?\s]*)""")
SDK_EXT = {".md", ".py", ".js", ".sh", ".yml", ".yaml", ".json", ".go", ".txt", ".toml"}
SITE_SKIP_DIRS = {".git", "node_modules", "docs", "legal", "tests", "scripts", "src", "admin", "petproof-agent", "rna-starter-kit-v1", "data"}
POST_ONLY = re.compile(r"/mcp(/|$)|/api/receipt/(emit|license|license-check|gumroad-webhook)$|/api/receipt-token$|/api/v1$")
PLACEHOLDER = re.compile(r"[{}$<>]|RECEIPT_ID|YOUR_|example\.(com|org)|localhost|127\.0\.0\.1|0\.0\.0\.0|www\.w3\.org/2000/")
# Sites that refuse automated requests (LinkedIn answers 999). Reported as BLOCKED: check by hand.
BOT_WALLED = re.compile(r"^https?://([a-z]+\.)?(linkedin\.com|x\.com|twitter\.com)/")


def clean(u: str) -> str:
    return u.rstrip(".,;:*_")


def collect(root: Path, website: bool) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root)
        if not f.is_file() or set(rel.parts[:-1]) & ({".git", "node_modules"} | (SITE_SKIP_DIRS if website else set())):
            continue
        if website:
            if not (f.suffix in {".html", ".txt", ".xml"} or rel.parts[0] == ".well-known" or rel.name == "_redirects"):
                continue
        elif f.suffix not in SDK_EXT or f.name == "package-lock.json":
            continue
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(lines, 1):
            if re.search(r'rel=["\'](preconnect|dns-prefetch)|xmlns|"@context"|"\$schema"', line):
                continue
            hits = [clean(u) for u in URL_RE.findall(line)]
            if website:
                hits += [SITE + p for p in HREF_RE.findall(line)]
                if rel.name == "_redirects" and line.strip() and not line.startswith("#"):
                    parts = line.split()
                    hits += [SITE + parts[0].rstrip("*"), SITE + parts[1]] if len(parts) >= 2 else []
            for u in hits:
                found.setdefault(u, set()).add(f"{root.name}/{rel}:{n}")
    return found


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: D401
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def check(url: str) -> tuple[str, list[str]]:
    chain: list[str] = []
    for _ in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": "inquiro-link-crawl/1.0"})
        try:
            with OPENER.open(req, timeout=30) as r:
                code, loc = r.status, None
        except urllib.error.HTTPError as e:
            code, loc = e.code, e.headers.get("Location")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            chain.append(f"ERR {getattr(e, 'reason', e)}")
            return "FAIL", chain
        chain.append(str(code))
        if code in (301, 302, 303, 307, 308) and loc:
            url = urllib.parse.urljoin(url, loc)
            chain[-1] += f"->{url}"
            continue
        if code != 200:
            return ("BLOCKED" if BOT_WALLED.match(url) and code in (403, 429, 999) else "FAIL"), chain
        temp = [c for c in chain[:-1] if not c.startswith(("301", "308"))]
        return ("WARN" if temp else "PASS"), chain
    return "FAIL", chain + ["too many redirects"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--website", help="path to a clone of the website repo")
    ap.add_argument("--list", action="store_true", help="list URLs without requesting them")
    args = ap.parse_args()

    urls = collect(Path(__file__).resolve().parent.parent, website=False)
    if args.website:
        for u, src in collect(Path(args.website).resolve(), website=True).items():
            urls.setdefault(u, set()).update(src)

    counts = {"PASS": 0, "WARN": 0, "BLOCKED": 0, "FAIL": 0, "SKIP": 0}
    for u in sorted(urls):
        src = ", ".join(sorted(urls[u])[:3]) + (f" +{len(urls[u]) - 3}" if len(urls[u]) > 3 else "")
        if PLACEHOLDER.search(u) or POST_ONLY.search(urllib.parse.urlparse(u).path):
            counts["SKIP"] += 1
            print(f"SKIP  {u}  <- {src}")
            continue
        if args.list:
            print(f"URL   {u}  <- {src}")
            continue
        status, chain = check(u)
        counts[status] += 1
        print(f"{status}  {' | '.join(chain)}  {u}  <- {src}", flush=True)
        time.sleep(0.2)
    print(f"\nlink crawl: {len(urls)} URLs | " + " ".join(f"{k}={v}" for k, v in counts.items()))
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
