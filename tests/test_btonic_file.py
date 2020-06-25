import struct
from pathlib import Path
from unittest.mock import patch

import pytest

from btonic.btonic_file import BtonicFile, BtonicHeader


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
        file = tmp_path / "test"
        file.write_bytes(b"expected")
        instance = BtonicFile(str(file))

        assert instance._file_object is None
        with instance:
            assert instance._mv.readonly
            assert instance._mv == b"expected"
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
        "attribute,initializer_func",
        [
            ("_header", "btonic.btonic_file.BtonicHeader.deserialize"),
            ("_segment_table", "btonic.btonic_file.BtonicFile._parse_segment_table"),
        ],
    )
    def test_initialize_file_metadata_initializes_needed_variables(
        self, attribute, initializer_func
    ):
        instance = BtonicFile("")
        instance._mv = memoryview(b"\x00" * (2 ** 16))

        with patch(initializer_func, return_value="expected"):
            instance._initialize_file_metadata()

        assert getattr(instance, attribute) == "expected"

    @pytest.mark.parametrize(
        "segment_list", [[(4, 10)], [(4, 10), (100, 31), (12, 20)],]
    )
    def test_parse_segment_table_returns_segment_list(self, segment_list):
        serialized_list = b"".join(
            [struct.pack(">II", *segment) for segment in segment_list]
        )
        serialized_list += b"\x00" * 8  # segment list is terminated by empty entry

        parsed_segments = BtonicFile._parse_segment_table(memoryview(serialized_list))

        assert len(parsed_segments) == len(segment_list)
        for i, (offset, size) in enumerate(segment_list):
            assert offset == parsed_segments[i].offset
            assert size == parsed_segments[i].size
