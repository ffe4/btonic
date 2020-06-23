import pytest

from btonic.btonic_file import BtonicHeader


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
def test_deserialize_btonic_header(data, expected):
    assert BtonicHeader.deserialize(data) == expected


@pytest.mark.parametrize(
    "init_args,expected",
    [
        ([b"EFS\x01"], b"EFS\x01" + b"\x00" * 28 + b"\x04" + b"\x00" * 31),
        ([b"\x00\xFFAB"], b"\x00\xFFAB" + b"\x00" * 28 + b"\x04" + b"\x00" * 31),
        ([], b"EFS\x01" + b"\x00" * 28 + b"\x04" + b"\x00" * 31),
    ],
)
def test_serialize_btonic_header(init_args, expected):
    header = BtonicHeader(*init_args)
    assert header.serialize() == expected
