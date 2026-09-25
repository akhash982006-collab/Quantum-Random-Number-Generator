"""Input detection and validation. Raw values are never silently altered."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class IngestionResult:
    bits: np.ndarray
    source_name: str
    source_type: str
    invalid_values: int
    duplicate_sections: int
    preprocessing: list[str]
    preview: str
    status: str


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[\s,;|]+", text.strip()) if token]


def ingest_bytes(raw: bytes, name: str = "uploaded stream") -> IngestionResult:
    preprocessing = ["Input read as bytes; no bit correction or denoising applied."]
    suffix = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    invalid = 0
    source_type = "binary bytes"
    values: list[int] = []
    try:
        decoded = raw.decode("utf-8")
        if suffix == "csv" or "," in decoded[:2048] or "\n" in decoded[:2048]:
            frame = pd.read_csv(io.StringIO(decoded), header=None)
            candidates = frame.astype(str).values.ravel().tolist()
            source_type = "CSV / text"
        else:
            candidates = _tokenize(decoded)
            source_type = "0/1 text"
        for candidate in candidates:
            if candidate in {"0", "1"}:
                values.append(int(candidate))
            elif candidate.strip() and re.fullmatch(r"[01]+", candidate.strip()):
                values.extend(int(char) for char in candidate.strip())
            elif candidate.strip():
                invalid += 1
    except UnicodeDecodeError:
        source_type = "raw binary bytes"
        for byte in raw:
            values.extend(int(bit) for bit in f"{byte:08b}")
        preprocessing.append("Raw bytes expanded to big-endian 8-bit representation.")
    bits = np.asarray(values, dtype=np.int8)
    duplicate_sections = 0
    if bits.size >= 128:
        chunks = [bytes(np.packbits(bits[i:i + 64])) for i in range(0, bits.size - 63, 64)]
        duplicate_sections = len(chunks) - len(set(chunks))
    if invalid:
        preprocessing.append(f"{invalid} invalid token(s) excluded from analysis and reported.")
    status = "VALID" if bits.size >= 64 and invalid == 0 else "VALID WITH WARNINGS" if bits.size >= 64 else "INSUFFICIENT DATA"
    preview = "".join(str(int(bit)) for bit in bits[:256])
    return IngestionResult(bits, name, source_type, invalid, duplicate_sections, preprocessing, preview, status)
