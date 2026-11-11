// Recompute an IPFS CIDv1 (raw codec, sha2-256) in the browser, so a receipt can be
// verified without trusting the server that served it.

const PREFIX = new Uint8Array([0x01, 0x55, 0x12, 0x20]);
const ALPHABET = "abcdefghijklmnopqrstuvwxyz234567";

function base32(bytes: Uint8Array): string {
  let bits = 0;
  let value = 0;
  let out = "";
  for (const byte of bytes) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      out += ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) out += ALPHABET[(value << (5 - bits)) & 31];
  return out;
}

export async function cidOf(bytes: Uint8Array): Promise<string> {
  if (!globalThis.crypto?.subtle) {
    throw new Error("Your browser only exposes WebCrypto on https:// or localhost.");
  }
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes as BufferSource));
  const full = new Uint8Array(PREFIX.length + digest.length);
  full.set(PREFIX);
  full.set(digest, PREFIX.length);
  return "b" + base32(full);
}

export async function verifyRemote(url: string, expected: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Couldn't download the receipt (${res.status})`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  const computed = await cidOf(bytes);
  return { computed, matches: computed === expected, size: bytes.length };
}
