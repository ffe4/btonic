from pathlib import Path

import pytest

from btonic.btonic_file import BtonicFile, BtonicHeader


class TestBtonicHeader:
    @pytest.mark.parametrize(
        "data,expected",
        [
            (b"EFS\x01" + b"\x00" * 28 + b"\x04" + b"\x00" * 31, BtonicHeader(b"EFS\x01")),
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
    def test_context_manager_sets_up_read_only_memoryview_and_closes_file_object(self, tmp_path: Path):
        file = tmp_path / "test"
        file.write_bytes(b"expected")
        instance = BtonicFile(str(file))

        assert instance._file_object is None
        with instance:
            assert instance._mv.readonly
            assert instance._mv == b"expected"
        assert instance._file_object.closed
