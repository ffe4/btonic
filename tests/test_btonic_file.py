import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from btonic.btonic_file import BlockList, BtonicFile, BtonicHeader


class TestBtonicHeader:
    @pytest.mark.parametrize(
        "data,expected",
        [
            (
                b"EFS\x01" + b"\x00" * 28 + b"\x04" + b"\x00" * 31,
                BtonicHeader(b"EFS\x01"),
            ),
            (b"EFS\x01" + b"\xFF" * 60, BtonicHeader(b"EFS\x01")),
            (
                b"\x00\xFFAB" + b"\x00" * 28 + b"\x04" + b"\x00" * 31,
                BtonicHeader(b"\x00\xFFAB"),
            ),
        ],
    )
    def test_deserialize_returns_correct_instance(self, data, expected):
        assert BtonicHeader.deserialize(data) == expected

    @pytest.mark.parametrize(
        "init_args,expected",
        [
            ([b"EFS\x01"], b"EFS\x01" + b"\x00" * 28 + b"\x04" + b"\x00" * 31),
            ([b"\x00\xFFAB"], b"\x00\xFFAB" + b"\x00" * 28 + b"\x04" + b"\x00" * 31),
            ([], b"EFS\x01" + b"\x00" * 28 + b"\x04" + b"\x00" * 31),
        ],
    )
    def test_serialize_returns_correct_bytes(self, init_args, expected):
        header = BtonicHeader(*init_args)
        assert header.serialize() == expected


class TestBtonicFile:
    def test_context_manager_sets_up_read_only_memoryview_and_closes_file_object(
        self, tmp_path: Path
    ):
        expected = b"\x01\x00" * (2 ** 10)
        file = tmp_path / "test"
        file.write_bytes(expected)
        instance = BtonicFile(str(file))

        assert instance._file_object is None
        with instance:
            assert instance._mv.readonly
            assert instance._mv == expected
        assert instance._file_object.closed

    def test_entering_context_calls_initialize_file_metadata(self, tmp_path: Path):
        file = tmp_path / "test"
        file.write_bytes(b"expected")

        with patch(
            "btonic.btonic_file.BtonicFile._initialize_file_metadata"
        ) as initialize:
            with BtonicFile(str(file)):
                pass

        initialize.assert_called_once_with()

    @pytest.mark.parametrize(
        "attribute", ["_header", "_block_list"],
    )
    def test_initialize_file_metadata_initializes_attributes(self, attribute):
        instance = BtonicFile("")
        instance._mv = memoryview(b"\x01\x00" * (2 ** 10))

        assert getattr(instance, attribute) is None
        instance._initialize_file_metadata()
        assert getattr(instance, attribute) is not None

    @pytest.mark.parametrize("block_list", [[(4, 10)], [(4, 10), (100, 31), (12, 20)]])
    def test_parse_block_table_returns_list_of_locations(self, block_list):
        serialized_list = b"".join([struct.pack(">II", *block) for block in block_list])
        serialized_list += b"\x00" * 8  # block list is terminated by empty entry

        parsed_blocks = BtonicFile._parse_block_table(memoryview(serialized_list))

        assert len(parsed_blocks) == len(block_list)
        for i, (offset, size) in enumerate(block_list):
            assert offset == parsed_blocks[i].offset
            assert size == parsed_blocks[i].size


class TestBlockList:
    def test_block_list_initialization(self, monkeypatch):
        mock_data_blocks = [
            b"MAIN\x00\x00\x00\x00\x00\x00dg\x00\x01\x00\x01",
            b"data\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02list\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03index\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x04",
            b"\x00",
            b"\x00",
            b"XYZ\x00\x00\x00\x00\x00\x00\x00abc\x00\x00\x05"
            b"EXPECTED\x00\x00def\x00\x00\x06",
            b"\x00",
            b"\x00",
        ]
        mock_locations = list(
            zip(range(len(mock_data_blocks)), range(1, len(mock_data_blocks) + 1))
        )
        expected_fields = [
            (None, None, True),
            ("MAIN", "dg", True),
            ("data", "", False),
            ("list", "", False),
            ("index", "", True),
            ("XYZ", "abc", False),
            ("EXPECTED", "def", False),
        ]

        mock_mem = MagicMock()
        mock_mem.__getitem__.side_effect = lambda x: mock_data_blocks[x.start]

        with patch("builtins.memoryview", return_value=mock_mem):
            block_list = BlockList(mock_locations, memoryview())

        for i, fields in enumerate(expected_fields):
            block = block_list[i]
            assert (block.name, block.ext, block.is_index) == fields

    @pytest.mark.parametrize(
        "index_block,expected",
        [
            (
                b"MAIN\x00\x00\x00\x00\x00\x00dg\x00\x01\x00\x01",
                [("MAIN", "dg", True, 1)],
            ),
            (
                b"data\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02ABCDEFGHIJKLM\x00\x00\x0bindex\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x04",
                [
                    ("data", "", False, 2),
                    ("ABCDEFGHIJ", "KLM", False, 11),
                    ("index", "", True, 4),
                ],
            ),
        ],
    )
    def test_parse_index_block_returns_records(self, index_block, expected):
        result = BlockList._parse_index_block(index_block)
        assert result == expected

    @pytest.mark.parametrize(
        "record,expected",
        [
            (
                b"MAIN\x00\x00\x00\x00\x00\x00dg\x00\x01\x00\x01",
                ("MAIN", "dg", True, 1),
            ),
            (
                b"data\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02",
                ("data", "", False, 2),
            ),
            (b"HEADWORD\x00\x00txi\x00\x00\x0a", ("HEADWORD", "txi", False, 10)),
        ],
    )
    def test_parse_block_record_returns_fields(self, record, expected):
        result = BlockList._parse_index_block_record(record)
        assert result == expected
