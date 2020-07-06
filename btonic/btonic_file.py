import logging
import struct
from collections import deque, namedtuple
from dataclasses import dataclass
from mmap import ACCESS_READ, mmap


@dataclass()
class DataBlock:
    mem_slice: slice
    name: str = None
    ext: str = None
    is_index: bool = None

    def __post_init__(self):
        if self.name and len(self.name.encode("utf-8")) > 10:
            raise ValueError("DataBlock name attribute cannot be longer than 10 bytes")
        if self.ext and len(self.ext.encode("utf-8")) > 3:
            raise ValueError("DataBlock ext attribute cannot be longer than 3 bytes")

    def serialize_index_record(self, block_index):
        b = b""
        b += self.name.encode("utf-8").ljust(10, b"\x00")
        b += self.ext.encode("utf-8").ljust(3, b"\x00")
        b += b"\x01" if self.is_index else b"\x00"
        b += struct.pack(">H", block_index)
        return b


class BlockList(list):
    def __init__(self, block_locations, mem: memoryview):
        blocks = [DataBlock(slice(block[0], sum(block))) for block in block_locations]
        blocks[0].is_index = True
        next_block_queue = deque([0])
        while next_block_queue:
            current_index = next_block_queue.popleft()
            for metadata in self._parse_index_block(
                bytes(mem[blocks[current_index].mem_slice])
            ):
                name, ext, is_index, index = metadata
                if is_index:
                    next_block_queue.append(index)
                block = blocks[index]
                block.name = name
                block.ext = ext
                block.is_index = is_index
        super().__init__(blocks)

    @staticmethod
    def _deserialize_index_block_record(data: bytes):
        return (
            # REVENG there's a good chance that names are restricted to 8 bytes.
            data[:10].rstrip(b"\x00").decode("utf-8"),
            data[10:13].rstrip(b"\x00").decode("utf-8"),
            *struct.unpack(">?H", data[13:16]),
        )

    @classmethod
    def _parse_index_block(cls, data: bytes):
        records = []
        for i in range(len(data) // 16):
            records.append(
                cls._deserialize_index_block_record(data[i * 16 : i * 16 + 16])
            )
        return records


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


class BtonicFile:
    def __init__(self, filename):
        self.filename = filename
        self._file_object = None
        self._header = None
        self._block_list = None

    def __enter__(self):
        self._file_object = open(self.filename, "rb")
        self._mmap = mmap(self._file_object.fileno(), 0, access=ACCESS_READ)
        self._mv = memoryview(self._mmap)
        self._initialize_file_metadata()
        return self

    def __exit__(self, *args):
        self._mv.release()
        self._mmap.close()
        self._file_object.close()

    def _initialize_file_metadata(self):
        self._header = BtonicHeader.deserialize(bytes(self._mv[0:64]))
        block_location_table = self._parse_block_table(bytes(self._mv[64:8256]))
        self._block_list = BlockList(block_location_table, self._mv)

    @staticmethod
    def _parse_block_table(data: bytes):
        BlockLocation = namedtuple("BlockLocation", ["offset", "size"])
        blocks = []
        for (offset, size) in struct.iter_unpack(">II", data):
            if not offset and not size:
                break
            blocks.append(BlockLocation(offset, size))
        return blocks

    def read_slice(self, s: slice):
        return bytes(self._mv[s])


def extract_files(filename):
    # TODO write tests and refactor into coherent codebase
    with BtonicFile(filename) as f:
        data_block, list_block = None, None
        for block in f._block_list:
            if all((data_block, list_block)):
                break
            if block.name == "data":
                data_block = f.read_slice(block.mem_slice)
            if block.name == "list":
                list_block = f.read_slice(block.mem_slice)
        # parse file list
        # --- DFLHEADER ---
        encoding = list_block[:8].rstrip(b"\x00").decode("ascii")
        encoding = {
            "XML-SJIS": "shift_jis",
            "XML-UTF8": "utf-8"
        }.get(encoding, "utf-8")
        # 8 unknown bytes
        (number_of_files, ofs_filelist, len_filename, ofs_filenames,) = struct.unpack(
            ">4I", list_block[16:32]
        )
        # 32 unknown bytes
        # --- DFLHEADER END ---
        record_size = 4 + len_filename  # add 4 byte ID
        filenames = {}
        files = []
        for i in range(number_of_files):
            filename_item = list_block[ofs_filenames + (record_size * i): ofs_filenames + (record_size * (i + 1))]
            # TODO maybe assert that id is not already in dict
            filenames[struct.unpack(">I", filename_item[:4])[0]] = (
                filename_item[4:].rstrip(b"\x00").decode(encoding)
            )
            file_property_item = list_block[ofs_filelist + (16 * i): ofs_filelist + (16 * (i + 1))]
            offset, size, storage_type, filename_id = struct.unpack(
                ">4I", file_property_item
            )
            File = namedtuple("File", ["filename", "storage_type", "slice", "data"])
            files.append(File(filenames[filename_id], storage_type, slice(offset, offset+size), b""))

        # TODO extract data

        return files
