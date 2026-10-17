"""Pure-Python BLAKE3 (default 32-byte hash) and Ed25519 signature verification.

Fallbacks for machines without the `blake3` or `cryptography` packages, so an
evaluator can verify receipts with nothing but Python 3.9+. Slow but exact.

BLAKE3: port of the reference implementation (github.com/BLAKE3-team/BLAKE3,
reference_impl). Ed25519: verification per RFC 8032 section 5.1.7.
"""
from __future__ import annotations

import hashlib

# --- BLAKE3 -----------------------------------------------------------------

_IV = (0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
       0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19)
_PERM = (2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8)
_CHUNK_START, _CHUNK_END, _PARENT, _ROOT = 1, 2, 4, 8
_BLOCK_LEN, _CHUNK_LEN = 64, 1024
_M32 = 0xFFFFFFFF


def _rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & _M32


def _g(s: list, a: int, b: int, c: int, d: int, mx: int, my: int) -> None:
    s[a] = (s[a] + s[b] + mx) & _M32
    s[d] = _rotr(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & _M32
    s[b] = _rotr(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b] + my) & _M32
    s[d] = _rotr(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & _M32
    s[b] = _rotr(s[b] ^ s[c], 7)


def _compress(cv: list, block: list, counter: int, block_len: int, flags: int) -> list:
    s = list(cv) + list(_IV[:4]) + [counter & _M32, (counter >> 32) & _M32, block_len, flags]
    m = list(block)
    for r in range(7):
        _g(s, 0, 4, 8, 12, m[0], m[1])
        _g(s, 1, 5, 9, 13, m[2], m[3])
        _g(s, 2, 6, 10, 14, m[4], m[5])
        _g(s, 3, 7, 11, 15, m[6], m[7])
        _g(s, 0, 5, 10, 15, m[8], m[9])
        _g(s, 1, 6, 11, 12, m[10], m[11])
        _g(s, 2, 7, 8, 13, m[12], m[13])
        _g(s, 3, 4, 9, 14, m[14], m[15])
        if r < 6:
            m = [m[i] for i in _PERM]
    for i in range(8):
        s[i] ^= s[i + 8]
        s[i + 8] ^= cv[i]
    return s


def _words(block: bytes) -> list:
    block = block.ljust(_BLOCK_LEN, b"\0")
    return [int.from_bytes(block[i:i + 4], "little") for i in range(0, _BLOCK_LEN, 4)]


def _chunk_output(chunk: bytes, counter: int):
    """Return (cv, block_words, counter, block_len, flags) of the chunk's last block."""
    cv = list(_IV)
    blocks = [chunk[i:i + _BLOCK_LEN] for i in range(0, len(chunk), _BLOCK_LEN)] or [b""]
    for i, block in enumerate(blocks):
        flags = (_CHUNK_START if i == 0 else 0) | (_CHUNK_END if i == len(blocks) - 1 else 0)
        if i == len(blocks) - 1:
            return cv, _words(block), counter, len(block), flags
        cv = _compress(cv, _words(block), counter, _BLOCK_LEN, flags)[:8]
    raise AssertionError("unreachable")


def _parent(left: list, right: list):
    return list(_IV), left + right, 0, _BLOCK_LEN, _PARENT


def blake3_hex(data: bytes) -> str:
    chunks = [data[i:i + _CHUNK_LEN] for i in range(0, len(data), _CHUNK_LEN)] or [b""]
    stack: list = []
    for counter, chunk in enumerate(chunks[:-1]):
        cv_in, block, ctr, blen, flags = _chunk_output(chunk, counter)
        cv = _compress(cv_in, block, ctr, blen, flags)[:8]
        total = counter + 1
        while total & 1 == 0:  # merge completed subtrees
            cv = _compress(*_parent(stack.pop(), cv))[:8]
            total >>= 1
        stack.append(cv)
    output = _chunk_output(chunks[-1], len(chunks) - 1)
    while stack:
        cv = _compress(*output)[:8]
        output = _parent(stack.pop(), cv)
    cv_in, block, ctr, blen, flags = output
    words = _compress(cv_in, block, ctr, blen, flags | _ROOT)[:8]
    return b"".join(w.to_bytes(4, "little") for w in words).hex()


# --- Ed25519 verification ---------------------------------------------------

_P = 2 ** 255 - 19
_Q = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _add(a, b):
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    A = (y1 - x1) * (y2 - x2) % _P
    B = (y1 + x1) * (y2 + x2) % _P
    C = 2 * t1 * t2 * _D % _P
    D = 2 * z1 * z2 % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return E * F % _P, G * H % _P, F * G % _P, E * H % _P


def _mul(s: int, pt):
    acc = (0, 1, 1, 0)
    while s:
        if s & 1:
            acc = _add(acc, pt)
        pt = _add(pt, pt)
        s >>= 1
    return acc


def _equal(a, b) -> bool:
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _decompress(raw: bytes):
    if len(raw) != 32:
        return None
    y = int.from_bytes(raw, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        if sign:
            return None
        x = 0
    else:
        x = pow(x2, (_P + 3) // 8, _P)
        if (x * x - x2) % _P:
            x = x * _SQRT_M1 % _P
        if (x * x - x2) % _P:
            return None
        if x & 1 != sign:
            x = _P - x
    return x, y, 1, x * y % _P


_BY = 4 * pow(5, _P - 2, _P) % _P
_B = _decompress(_BY.to_bytes(32, "little"))


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    if len(signature) != 64:
        return False
    A = _decompress(public_key)
    R = _decompress(signature[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _Q:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public_key + message).digest(), "little") % _Q
    return _equal(_mul(s, _B), _add(R, _mul(h, A)))
