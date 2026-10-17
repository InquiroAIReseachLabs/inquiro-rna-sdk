"""Signed checkpoints of a ledger's head, and key pinning. No network.

A checkpoint states which ledger (`origin`), how far it reached (`seq`), its
last receipt hash (`head`), when (`time`) and which key signed it (`key_id`).
It is plain JSON under the kit's canonical rule (compact, keys sorted, ASCII only):

    v, origin, seq, head, time, key_id,
    checkpoint_hash (dual hash of the canonical body: the six fields above),
    signature (Ed25519 over the ASCII bytes of checkpoint_hash, hex)

The stored form is the canonical JSON of all eight fields plus one LF. Those
exact bytes are what is signed over (via checkpoint_hash), stored, bundled and
compared; any other byte form is rejected. A checkpoint is trusted only when
its key_id is pinned: in a pin file, or the one public key named by the caller.

Standalone like verify.py: standard library plus the optional native packages,
so it can travel in an evaluator bundle. Signing needs `cryptography`.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from offline.verify import GENESIS, canonical, dual_hash, key_id, signature_ok, verify_ledger
except ImportError:  # running from an evaluator bundle
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from verify import GENESIS, canonical, dual_hash, key_id, signature_ok, verify_ledger

CHECKPOINT_VERSION = 1
BODY_FIELDS = ("v", "origin", "seq", "head", "time", "key_id")
ALL_FIELDS = BODY_FIELDS + ("checkpoint_hash", "signature")

# Outcome codes. Stable: scripts and tests match on them.
CKPT_MALFORMED = "CKPT_MALFORMED"                # not a checkpoint: bad JSON, field, type or value
CKPT_VERSION = "CKPT_VERSION"                    # unknown format version
CKPT_NOT_CANONICAL = "CKPT_NOT_CANONICAL"        # bytes are not the one canonical form
CKPT_HASH_MISMATCH = "CKPT_HASH_MISMATCH"        # a field changed after signing
CKPT_KEY_UNPINNED = "CKPT_KEY_UNPINNED"          # signed by a key the verifier does not pin
CKPT_SIGNATURE_INVALID = "CKPT_SIGNATURE_INVALID"  # signature does not verify for the pinned key
CKPT_LEDGER_INVALID = "CKPT_LEDGER_INVALID"      # refused to sign: the ledger does not verify
CKPT_CONFLICT = "CKPT_CONFLICT"                  # a stored checkpoint for this seq has another head
PIN_INVALID = "PIN_INVALID"                      # pin file entry whose key_id does not match its key

HASH_RE = re.compile(r"^[0-9a-f]{64}:[0-9a-f]{64}$")
KEY_ID_RE = re.compile(r"^[0-9a-f]{16}$")
SIGNATURE_RE = re.compile(r"^[0-9a-f]{128}$")
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ORIGIN_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}(/[A-Za-z0-9._:-]{1,64}){2,4}$")
MAX_SEQ = 2 ** 53 - 1  # exact in every JSON implementation


class CheckpointError(ValueError):
    """A checkpoint was rejected (or could not be made). `code` is one of the constants above."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def check_fields(ckpt) -> None:
    """Raise CheckpointError unless ckpt has exactly the v1 fields with valid values."""
    if not isinstance(ckpt, dict):
        raise CheckpointError(CKPT_MALFORMED, "not a JSON object")
    if not _is_int(ckpt.get("v")):
        raise CheckpointError(CKPT_MALFORMED, "v must be an integer")
    if ckpt["v"] != CHECKPOINT_VERSION:
        raise CheckpointError(CKPT_VERSION, f"unknown checkpoint version {ckpt['v']}")
    keys = set(ckpt)
    expected = set(ALL_FIELDS) if keys >= {"checkpoint_hash", "signature"} else set(BODY_FIELDS)
    if keys != expected:
        missing, extra = sorted(expected - keys), sorted(keys - expected)
        raise CheckpointError(CKPT_MALFORMED, f"fields: missing {missing}, unexpected {extra}")
    origin, seq, head, ts = ckpt["origin"], ckpt["seq"], ckpt["head"], ckpt["time"]
    if not isinstance(origin, str) or not ORIGIN_RE.match(origin):
        raise CheckpointError(CKPT_MALFORMED, "origin must be 3 to 5 '/'-separated segments of [A-Za-z0-9._:-]")
    if not _is_int(seq) or not 0 <= seq <= MAX_SEQ:
        raise CheckpointError(CKPT_MALFORMED, "seq must be a non-negative integer")
    if not isinstance(head, str) or not HASH_RE.match(head):
        raise CheckpointError(CKPT_MALFORMED, "head must be sha256_hex:blake3_hex")
    if seq == 0 and head != GENESIS:
        raise CheckpointError(CKPT_MALFORMED, "a checkpoint at seq 0 must have the genesis head")
    if not isinstance(ts, str) or not TIME_RE.match(ts):
        raise CheckpointError(CKPT_MALFORMED, "time must be YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise CheckpointError(CKPT_MALFORMED, f"time {ts} is not a real date and time")
    if not isinstance(ckpt["key_id"], str) or not KEY_ID_RE.match(ckpt["key_id"]):
        raise CheckpointError(CKPT_MALFORMED, "key_id must be 16 lowercase hex characters")
    if "signature" in ckpt:
        if not isinstance(ckpt["checkpoint_hash"], str) or not HASH_RE.match(ckpt["checkpoint_hash"]):
            raise CheckpointError(CKPT_MALFORMED, "checkpoint_hash must be sha256_hex:blake3_hex")
        if not isinstance(ckpt["signature"], str) or not SIGNATURE_RE.match(ckpt["signature"]):
            raise CheckpointError(CKPT_MALFORMED, "signature must be 128 lowercase hex characters")


def body(ckpt: dict) -> dict:
    return {k: ckpt[k] for k in BODY_FIELDS}


def to_bytes(ckpt: dict) -> bytes:
    """The one stored byte form: canonical JSON plus one LF."""
    return canonical(ckpt) + b"\n"


def parse(data: bytes) -> dict:
    """Parse stored checkpoint bytes. Checks fields and canonical form, not the signature."""
    try:
        ckpt = json.loads(data.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raise CheckpointError(CKPT_MALFORMED, "not ASCII JSON")
    check_fields(ckpt)
    if "signature" not in ckpt:
        raise CheckpointError(CKPT_MALFORMED, "unsigned: checkpoint_hash and signature missing")
    if to_bytes(ckpt) != data:
        raise CheckpointError(CKPT_NOT_CANONICAL,
                              "bytes differ from the canonical form (re-indented, reordered, CRLF, or missing final LF)")
    return ckpt


def verify(data: bytes, pins: dict) -> dict:
    """Verify stored checkpoint bytes against pinned keys {key_id: raw 32-byte public key}.

    Returns the checkpoint dict, or raises CheckpointError. Order is fixed so the code
    is deterministic: form, then checkpoint_hash, then pin, then signature.
    """
    ckpt = parse(data)
    if dual_hash(canonical(body(ckpt))) != ckpt["checkpoint_hash"]:
        raise CheckpointError(CKPT_HASH_MISMATCH, "checkpoint_hash does not match the fields (a field was changed)")
    public = pins.get(ckpt["key_id"])
    if public is None:
        raise CheckpointError(CKPT_KEY_UNPINNED, f"key {ckpt['key_id']} is not pinned; refusing to trust it")
    if key_id(public) != ckpt["key_id"]:
        raise CheckpointError(PIN_INVALID, f"pinned entry for {ckpt['key_id']} holds a different key")
    if not signature_ok(public, ckpt["checkpoint_hash"].encode("ascii"), bytes.fromhex(ckpt["signature"])):
        raise CheckpointError(CKPT_SIGNATURE_INVALID, "signature does not verify for the pinned key")
    return ckpt


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sign(origin: str, seq: int, head: str, time: str, private_key) -> bytes:
    """Build and sign a checkpoint; returns the stored bytes. Needs `cryptography`."""
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    b = {"v": CHECKPOINT_VERSION, "origin": origin, "seq": seq, "head": head, "time": time, "key_id": key_id(raw)}
    check_fields(b)
    h = dual_hash(canonical(b))
    return to_bytes({**b, "checkpoint_hash": h, "signature": private_key.sign(h.encode("ascii")).hex()})


# --- offline ledgers ---------------------------------------------------------

def ledger_origin(kid: str, genesis_receipt_hash: str) -> str:
    """offline/<key_id>/<instance>: the instance is the seq 1 receipt, so a replaced ledger is a new origin."""
    return f"offline/{kid}/{genesis_receipt_hash.split(':')[0][:16]}"


def ledger_state(lines) -> tuple[str, int, str]:
    """(genesis receipt_hash, last seq, last receipt_hash) of a ledger's non-empty lines."""
    receipts = [json.loads(line) for line in lines if line.strip()]
    if not receipts:
        raise CheckpointError(CKPT_LEDGER_INVALID, "ledger is empty")
    return receipts[0]["receipt_hash"], receipts[-1]["seq"], receipts[-1]["receipt_hash"]


def for_ledger(ledger, private_key, time: str | None = None) -> bytes:
    """Checkpoint of a whole ledger's head. Refuses unless the ledger verifies with this key."""
    from cryptography.hazmat.primitives import serialization

    raw = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    lines = Path(ledger).read_text(encoding="utf-8").splitlines()
    result = verify_ledger(lines, raw)
    if not result["ok"]:
        first = result["issues"][0]
        raise CheckpointError(CKPT_LEDGER_INVALID, f"ledger does not verify (line {first['line']}: {first['problem']}); "
                                                   "no checkpoint signed")
    genesis, seq, head = ledger_state(lines)
    return sign(ledger_origin(key_id(raw), genesis), seq, head, time or now_utc(), private_key)


def checkpoint_dir(ledger) -> Path:
    ledger = Path(ledger)
    return ledger.with_name(ledger.stem + ".checkpoints")


def store(ledger, data: bytes) -> tuple[Path, bool]:
    """Write a checkpoint beside its ledger as <stem>.checkpoints/<seq>.ckpt, never rewriting one.

    Returns (path, written). An existing file for the same seq is kept if it states the
    same origin and head; if it states another, raises CKPT_CONFLICT.
    """
    ckpt = parse(data)
    folder = checkpoint_dir(ledger)
    folder.mkdir(exist_ok=True)
    path = folder / f"{ckpt['seq']:012d}.ckpt"
    try:
        with open(path, "xb") as f:  # binary, exclusive: no newline translation, no overwrite
            f.write(data)
        return path, True
    except FileExistsError:
        old = parse(path.read_bytes())
        if (old["origin"], old["head"]) != (ckpt["origin"], ckpt["head"]):
            raise CheckpointError(CKPT_CONFLICT, f"{path} already states a different head for seq {ckpt['seq']}")
        return path, False


# --- key pinning -------------------------------------------------------------

def load_pins(path) -> dict:
    """Pin file -> {key_id: raw public key}. Every entry's key_id must match its key."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = doc["keys"]
    except (OSError, ValueError, KeyError, TypeError):
        raise CheckpointError(PIN_INVALID, f"{path} is not a pin file ({{\"v\": 1, \"keys\": [...]}})")
    pins = {}
    for e in entries:
        try:
            raw = base64.b64decode(e["public_key"], validate=True)
        except (KeyError, TypeError, ValueError):
            raise CheckpointError(PIN_INVALID, f"entry {e!r} has no valid base64 public_key")
        if len(raw) != 32 or key_id(raw) != e.get("key_id"):
            raise CheckpointError(PIN_INVALID, f"entry {e.get('key_id')!r} does not match its public key")
        pins[e["key_id"]] = raw
    return pins


def pin_one(public_key: bytes) -> dict:
    """Pins holding exactly one key, for callers that name a public key directly."""
    return {key_id(public_key): public_key}


# --- verifier memory: the highest head seen per origin and key ---------------
#
# Optional local state. It turns "this checkpoint verifies" into "this checkpoint
# is not older than, and does not contradict, one I saw before". It is only as
# good as the file: delete it and the verifier forgets (THREAT_MODEL.md).

ROLLBACK = "ROLLBACK"                            # below a head this verifier has already seen
SPLIT_VIEW = "SPLIT_VIEW"                        # same seq, different head: two histories
LEDGER_RESET = "LEDGER_RESET"                    # notice: new instance of an ephemeral ledger
PERSISTENCE_DOWNGRADE = "PERSISTENCE_DOWNGRADE"  # a persistent origin now claims to be ephemeral
ORIGIN_MISMATCH = "ORIGIN_MISMATCH"              # a checkpoint of another ledger
REPLACED = "REPLACED"                            # same key, different first receipt: a rebuilt ledger
MEMORY_INVALID = "MEMORY_INVALID"


def load_memory(path) -> dict:
    """Memory file -> {"v": 1, "heads": {origin: {key_id: {"seq", "head", "seen"}}}}; empty if absent."""
    path = Path(path)
    if not path.exists():
        return {"v": 1, "heads": {}}
    try:
        memory = json.loads(path.read_text(encoding="utf-8"))
        assert memory["v"] == 1 and isinstance(memory["heads"], dict)
        for keys in memory["heads"].values():
            for m in keys.values():
                assert _is_int(m["seq"]) and isinstance(m["head"], str)
    except (OSError, ValueError, KeyError, TypeError, AssertionError, AttributeError):
        raise CheckpointError(MEMORY_INVALID, f"{path} is not a verifier memory file; refusing to guess")
    return memory


def save_memory(path, memory: dict) -> None:
    """Replace the memory file in one step (write a temporary file, then rename over it)."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(memory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def remembered(memory: dict, origin: str, kid: str):
    return memory["heads"].get(origin, {}).get(kid)


def remember(memory: dict, origin: str, kid: str, seq: int, head: str) -> None:
    """Record a head if it is higher than the one held for this origin and key."""
    held = remembered(memory, origin, kid)
    if held is None or seq > held["seq"]:
        memory["heads"].setdefault(origin, {})[kid] = {"seq": seq, "head": head, "seen": now_utc()}


def head_against_memory(memory: dict, origin: str, kid: str, seq: int, head: str) -> list:
    """[(code, message)] for a head presented as current."""
    held = remembered(memory, origin, kid)
    if held is None:
        return []
    if seq < held["seq"]:
        return [(ROLLBACK, f"rollback: {origin} is presented at seq {seq}, but this verifier already saw "
                           f"seq {held['seq']} (on {held.get('seen', '?')})")]
    if seq == held["seq"] and head != held["head"]:
        return [(SPLIT_VIEW, f"split view: seq {seq} of {origin} has a different head than the one this "
                             "verifier saw before; two different histories exist")]
    return []


def pilot_parts(origin: str):
    """(persistence, deployment, tenant, instance or None) for a pilot origin, else None."""
    parts = origin.split("/")
    if parts[0] != "pilot" or len(parts) not in (4, 5) or parts[1] not in ("persistent", "ephemeral"):
        return None
    if (parts[1] == "ephemeral") != (len(parts) == 5):
        return None
    return parts[1], parts[2], parts[3], parts[4] if len(parts) == 5 else None


def origin_against_memory(memory: dict, origin: str) -> tuple[list, list]:
    """(issues, notices) from other origins of the same pilot deployment and tenant.

    An ephemeral ledger that restarted is a new instance: a notice, never tamper or
    rollback. A deployment remembered as persistent that now presents an ephemeral
    origin is refused: that is how a wiped persistent ledger would be disguised.
    """
    mine = pilot_parts(origin)
    if mine is None:
        return [], []
    issues, notices = [], []
    for other in sorted(memory["heads"]):
        theirs = pilot_parts(other)
        if other == origin or theirs is None or theirs[1:3] != mine[1:3]:
            continue
        if mine[0] == "ephemeral" and theirs[0] == "persistent":
            issues.append((PERSISTENCE_DOWNGRADE, f"{origin} claims an ephemeral ledger, but this verifier has seen "
                                                  f"{other} as persistent; a persistent ledger does not reset"))
        elif mine[0] == "ephemeral" and theirs[0] == "ephemeral" and not notices:
            notices.append((LEDGER_RESET, f"ledger reset: {origin} is a new instance of an ephemeral ledger "
                                          f"(seen before: {other}). Earlier checkpoints cannot be checked "
                                          "against it. This is a restart, not tampering."))
    return issues, notices


def compare(a: dict, b: dict) -> tuple[str, str, bool]:
    """Two verified checkpoints held by two parties: (code, message, consistent)."""
    if a["origin"] != b["origin"]:
        pa, pb = pilot_parts(a["origin"]), pilot_parts(b["origin"])
        if pa and pb and pa[1:3] == pb[1:3]:
            if pa[0] == pb[0] == "ephemeral":
                return LEDGER_RESET, "different instances of an ephemeral ledger: a restart between them, not tampering", True
            return PERSISTENCE_DOWNGRADE, "one checkpoint says persistent, the other ephemeral, for the same deployment", False
        oa, ob = a["origin"].split("/"), b["origin"].split("/")
        if oa[0] == ob[0] == "offline" and oa[1] == ob[1]:
            return REPLACED, ("same key, different first receipt: two different ledgers. If they should be one, "
                              "one of them was rebuilt; the earlier stored checkpoint decides which"), False
        return ORIGIN_MISMATCH, f"checkpoints of different ledgers ({a['origin']} and {b['origin']})", False
    if a["seq"] == b["seq"]:
        if a["head"] == b["head"]:
            return "CONSISTENT", f"same head at seq {a['seq']}", True
        return SPLIT_VIEW, f"split view: seq {a['seq']} has two different heads; two histories exist", False
    lo, hi = sorted((a, b), key=lambda c: c["seq"])
    return ("SEQ_DIFFERS", f"seq {lo['seq']} and seq {hi['seq']} of the same ledger. They are consistent only if "
            f"the ledger at seq {lo['seq']} has head {lo['head'][:16]}...: check with "
            "verify LEDGER KEY --checkpoint for both", True)
