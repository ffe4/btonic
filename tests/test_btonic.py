from io import BufferedReader
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

import btonic

TEST_DATA_DIR = Path(__file__).parents[0] / "test_data"


def test_version():
    assert btonic.__version__ == "0.1.0"


@pytest.mark.skipif(
    not TEST_DATA_DIR.exists(), reason="test data not found",
)
@pytest.mark.xfail(reason="not yet implemented", run=False)
def test_converts_nhk_btonic_file_to_xml(tmp_path):
    runner = CliRunner()
    file = TEST_DATA_DIR / "nhk.exi"
    output = tmp_path / "nhk.xml"

    result = runner.invoke(btonic.main, [str(file), str(output)])

    assert result.exit_code == 0
    with open(TEST_DATA_DIR / "nhk.xml", "rb") as f:
        assert output.read_bytes() == f.read()


@patch("btonic.btonic.convert")
def test_cli_passes_converter_correct_input_file(convert, tmp_path):
    runner = CliRunner()
    output = tmp_path / "output.xml"
    file = tmp_path / "input.exi"
    file.write_bytes(b"")

    runner.invoke(btonic.main, [str(file), str(output)])

    convert.assert_called_once()
    assert isinstance(convert.call_args.args[0], BufferedReader)
    assert convert.call_args.args[0].name == str(file)


def test_cli_correctly_writes_converter_result_to_output_file(tmp_path):
    runner = CliRunner()
    output = tmp_path / "output.xml"
    file = tmp_path / "input.exi"
    file.write_bytes(b"")

    with patch("btonic.btonic.convert", return_value=b"expected"):
        result = runner.invoke(btonic.main, [str(file), str(output)])

    assert result.exit_code == 0
    assert output.read_bytes() == b"expected"
