import logging
from dataclasses import dataclass


@dataclass
class BtonicHeader:
    """Header at the beginning of each BTONIC file."""

    # REVENG btonic header format beyond magic number
    magic_number: bytes = b"EFS\x01"

    @classmethod
    def deserialize(cls, data: bytes) -> "BtonicHeader":
        magic_number = data[:4]

        if magic_number != b"EFS\x01":
            logging.debug(
                f"Header contains unknown magic number: {repr(magic_number)}."
            )
        if data[4:32] != b"\x00" * 28:
            logging.debug(
                f"Header has bytes in first half after magic number: {repr(data[4:32])}"
            )
        if data[32:64] != b"\x04" + b"\x00" * 31:
            logging.debug(
                f"Header has different bytes in second half: {repr(data[32:64])}"
            )

        return BtonicHeader(magic_number)

    def serialize(self) -> bytes:
        return self.magic_number + b"\x00" * 28 + b"\x04" + b"\x00" * 31
        pass
