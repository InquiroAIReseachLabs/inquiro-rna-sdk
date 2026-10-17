"""Canonical JSON for RNA attestation payloads. Server and verifier must use the same bytes."""
from __future__ import annotations

import json
from typing import Any, Mapping


def canonical_bytes(obj: Mapping[str, Any] | dict[str, Any]) -> bytes:
    """Deterministic UTF-8 bytes: sorted keys, no extra whitespace (matches json.dumps default separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
