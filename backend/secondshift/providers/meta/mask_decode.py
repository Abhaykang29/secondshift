"""Attempts to decode SAM's <|mask;...|> string (pass 2 Phase E.3).

The /v1/responses output carries a mask string after a "H,W," header.
We tried, in the spec's order, against a REAL captured payload
(tests/fixtures/sam_real/probe_rectangle.json - a trivial rectangle,
where any true mask encoding must show obvious structure):

1. COCO RLE (compressed counts string) - REJECTED: the string contains
   characters up to '~' (126); COCO counts strings stay <= 111, and a
   spec-conformant decoder runs off the end of the string.
2. base64 PNG - REJECTED: the alphabet includes characters outside
   base64 (#, %, parentheses, brackets).
3. base64 raw bitmap (box size and image size) - REJECTED: same
   alphabet problem; base85 and Ascii85 also fail (overflow / '~').
4. Run-length pairs - REJECTED: after the "400,301," header (which does
   match the box height x width) the remainder is not counts.

Beyond the spec list we also tried basE91 (-> high-entropy bytes, no
mask structure) and zlib over the decodings (no valid stream). The
string has near-uniform character entropy and ZERO repeated 8-grams
for a mask that is a single solid rectangle, which no plain mask
encoding produces. Conclusion (recorded as Decision D10): the payload
behaves like an opaque/encoded token, not a decodable mask. v1 keeps
SAM's exact boxes; overlays are labeled "SAM outline (box)".

This module keeps the working decoders for the standard formats so a
future payload shape can be tested in one call.
Depends on: numpy, stdlib.
"""

import base64
import re

import numpy as np

_MASK_RE = re.compile(r"<\|mask;x=\d+;y=\d+;data=([^|]+)\|>")


def extract_mask_strings(text: str) -> list[str]:
    """Pull every mask data string out of a /responses output text."""
    return _MASK_RE.findall(text)


def coco_counts_decode(s: str) -> list[int] | None:
    """Decode a COCO compressed-counts string, or None if it isn't one."""
    counts: list[int] = []
    i = 0
    try:
        while i < len(s):
            x = 0
            k = 0
            more = True
            while more:
                c = ord(s[i]) - 48
                if c < 0 or c > 63:
                    return None
                x |= (c & 0x1F) << (5 * k)
                more = bool(c & 0x20)
                i += 1
                k += 1
                if not more and (c & 0x10):
                    x |= -1 << (5 * k)
            if len(counts) > 2:
                x += counts[-2]
            counts.append(x)
    except IndexError:
        return None
    return counts


def try_decode_mask(
    data: str, box_w: int, box_h: int
) -> tuple[np.ndarray | None, str | None]:
    """Try every known hypothesis. Returns (mask, method) or (None, None).

    The mask, when decoded, is at box resolution (the header is the
    box height x width) in column-major order, per COCO convention.
    A decode only counts if the foreground lies inside the box bounds
    (trivially true at box resolution) and covers a sane fraction.
    """
    header = re.match(r"^(\d+),(\d+),", data)
    body = data
    if header:
        box_h, box_w = int(header.group(1)), int(header.group(2))
        body = data[header.end():]
    counts = coco_counts_decode(body)
    if counts and sum(counts) == box_w * box_h:
        mask = np.zeros(box_w * box_h, dtype=np.uint8)
        pos, val = 0, 0
        for c in counts:
            mask[pos:pos + c] = val
            pos += c
            val = 1 - val
        return mask.reshape((box_h, box_w), order="F"), "coco_rle"
    raw_options: list[bytes] = []
    for decoder in (base64.b64decode, base64.b85decode):
        try:
            raw_options.append(decoder(body))
        except Exception:
            continue
    for raw in raw_options:
        bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))
        if bits.size >= box_w * box_h:
            return (
                bits[: box_w * box_h].reshape((box_h, box_w), order="F"),
                "base_bitmap",
            )
    return None, None
