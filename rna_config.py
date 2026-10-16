"""SDK endpoint settings. The default host lives in rna.config.json; RNA_BASE_URL overrides it."""
from __future__ import annotations

import json
import os
from pathlib import Path

_CONFIG = json.loads((Path(__file__).resolve().parent / "rna.config.json").read_text(encoding="utf-8"))


def base_url() -> str:
    """MCP endpoint for submit/verify calls (Render flight recorder demo by default)."""
    return os.environ.get("RNA_BASE_URL") or _CONFIG["base_url"]


def health_url() -> str:
    """GET /health on the same host as base_url()."""
    url = base_url().rstrip("/")
    return (url[: -len("/mcp")] if url.endswith("/mcp") else url) + "/health"


def verify_url() -> str:
    """Public verify-only MCP endpoint (rna_verify)."""
    return _CONFIG["verify_url"]


if __name__ == "__main__":
    print(base_url())
