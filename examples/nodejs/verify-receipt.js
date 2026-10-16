/**
 * Standalone merged-receipt verifier (Node 18+).
 * npm install  (installs @noble/hashes)
 * Usage: node verify-receipt.js path/to/merged.json [--tamper-test]
 */
import { blake3 } from "@noble/hashes/blake3.js";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

function canonicalStringify(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((x) => canonicalStringify(x)).join(",")}]`;
  }
  const keys = Object.keys(value).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalStringify(value[k])}`).join(",")}}`;
}

function splitReceiptHash(value) {
  const i = value.indexOf(":");
  if (i < 0) throw new Error("receipt_hash must be sha256_hex:blake3_hex");
  const sha = value.slice(0, i);
  const b3 = value.slice(i + 1);
  if (sha.length !== 64 || b3.length !== 64) {
    throw new Error("receipt_hash components must be 64 hex chars each");
  }
  return { sha, b3 };
}

function verifyMerged(doc) {
  const rh = doc.receipt_hash;
  if (typeof rh !== "string") throw new Error("receipt_hash missing");
  const { sha: wantSha, b3: wantB3 } = splitReceiptHash(rh);
  const body = {
    device_id: doc.device_id,
    event_type: doc.event_type,
    payload: doc.payload,
    signature: doc.signature,
    timestamp: doc.timestamp,
  };
  const bytes = new TextEncoder().encode(canonicalStringify(body));
  const shaHex = createHash("sha256").update(bytes).digest("hex");
  const b3d = blake3(bytes);
  const b3Hex = Array.from(b3d)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  const ok = shaHex === wantSha && b3Hex === wantB3;
  console.log("SHA256 match:", shaHex === wantSha);
  console.log("BLAKE3 match:", b3Hex === wantB3);
  console.log(ok ? "VERIFIED" : "FAILED");
  return ok;
}

// Endpoint: RNA_BASE_URL, else rna.config.json at the repo root.
async function baseUrl() {
  if (process.env.RNA_BASE_URL) return process.env.RNA_BASE_URL;
  const cfg = JSON.parse(await readFile(new URL("../../rna.config.json", import.meta.url), "utf8"));
  return cfg.base_url;
}

async function call(url, name, args) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: "1", method: "tools/call", params: { name, arguments: args } }),
  });
  const res = (await r.json()).result || {};
  return res.content?.[0]?.text ? { ...res, ...JSON.parse(res.content[0].text) } : res;
}

// Live receipt hashes cover server-assigned fields, so the tamper test asks
// the server: the real hash must verify and a one-character change must not.
async function tamperTest() {
  const url = await baseUrl();
  const attestation = {
    event_type: "identity_verified",
    device_id: "TAMPER-TEST-NODE",
    payload: { test: "tamper_detection" },
    timestamp: new Date().toISOString(), // fresh: the server rejects replays
    signature: "dGVzdA==", // any non-empty value passes on the public demo tenant
  };
  const sub = await call(url, "submit_attestation", attestation);
  const rh = sub.receipt_hash || (sub.receipt && `${sub.receipt.sha256}:${sub.receipt.blake3}`);
  if (!rh) throw new Error(`no receipt_hash (accepted=${sub.accepted})`);
  const flipped = rh.slice(0, -1) + (rh.endsWith("0") ? "1" : "0");
  if ((await call(url, "verify_receipt", { receipt_hash: rh })).valid !== true) throw new Error("original should verify");
  if ((await call(url, "verify_receipt", { receipt_hash: flipped })).valid !== false) throw new Error("tampered must fail");
  console.log("Tamper detection: WORKING");
}

const arg = process.argv[2];
if (arg === "--tamper-test") {
  tamperTest().catch((e) => {
    console.error(e);
    process.exit(1);
  });
} else if (!arg) {
  console.error("Usage: node verify-receipt.js <merged.json> | --tamper-test");
  process.exit(1);
} else {
  const doc = JSON.parse(await readFile(arg, "utf8"));
  process.exit(verifyMerged(doc) ? 0 : 1);
}
