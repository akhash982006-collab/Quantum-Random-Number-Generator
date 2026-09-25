"""Strict input contracts. No cleaning of corrupt input is performed."""
import hashlib
import io
from pathlib import Path
import numpy as np
import pandas as pd

MAX_BITS = 10_000_000

def validate(bits):
    a = np.asarray(bits)
    if a.ndim != 1 or not len(a) or len(a) > MAX_BITS:
        raise ValueError('Supply between 1 and 10,000,000 bits in one dimension.')
    if not np.isin(a, [0, 1]).all():
        raise ValueError('Only binary values 0 and 1 are allowed.')
    return a.astype(np.uint8)

def digest(bits):
    return hashlib.sha256(len(bits).to_bytes(8, 'big') + np.packbits(bits).tobytes()).hexdigest()

def ingest(raw, name):
    if len(raw) > 40_000_000:
        raise ValueError('File exceeds 40 MB transport limit.')
    suffix = Path(name).suffix.lower()
    if suffix == '.bin':
        if len(raw)*8 > MAX_BITS:
            raise ValueError('Decoded stream exceeds 10 million bits.')
        bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder='big')
    elif suffix == '.txt':
        text = raw.decode('utf-8-sig')
        if any(c not in '01' and not c.isspace() for c in text):
            raise ValueError('Text contains a character other than 0, 1, or whitespace.')
        bits = np.fromiter((int(c) for c in text if not c.isspace()), dtype=np.uint8)
    elif suffix == '.csv':
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False, skip_blank_lines=False)
        if list(df.columns) != ['bit'] or not df['bit'].isin(['0','1']).all():
            raise ValueError('CSV must have exactly one column named bit, containing only 0 or 1.')
        bits = df['bit'].to_numpy(dtype=np.uint8)
    else:
        raise ValueError('Supported file types: .txt, .csv, .bin.')
    bits = validate(bits)
    return bits, dict(name=name, bits=len(bits), sha256=digest(bits), file_sha256=hashlib.sha256(raw).hexdigest(), bit_order='MSB first', source='file')
