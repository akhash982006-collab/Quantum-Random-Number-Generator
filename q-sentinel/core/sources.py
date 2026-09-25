from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np

@dataclass
class BitChunk:
    sequence: int
    offset: int
    bits: np.ndarray

class DataSource(ABC):
    @abstractmethod
    def chunks(self, size=10000):
        """Yield ordered BitChunk objects; offsets count bits, not bytes."""

class FileSource(DataSource):
    def __init__(self, bits):
        self.bits = bits
    def chunks(self, size=10000):
        for seq, offset in enumerate(range(0, len(self.bits), size)):
            yield BitChunk(seq, offset, self.bits[offset:offset+size])

class SimulatorSource(FileSource):
    pass

def checked_chunks(source, size=10000):
    offset = 0
    for sequence, chunk in enumerate(source.chunks(size)):
        if chunk.sequence != sequence or chunk.offset != offset:
            raise ValueError('Acquisition discontinuity: missing, duplicate, or out-of-order chunk.')
        offset += len(chunk.bits)
        yield chunk
