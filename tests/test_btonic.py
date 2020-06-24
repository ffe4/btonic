from pathlib import Path
from unittest.mock import Mock, patch

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
def test_converts_nhk_btonic_file_to_xml(tmp_path: Path):
    runner = CliRunner()
    input_file = TEST_DATA_DIR / "nhk.exi"
    output_directory = tmp_path / "out"
    output_directory.mkdir(exist_ok=False)
    output_file = output_directory / "Accent.xml"

    result = runner.invoke(btonic.main, [str(input_file), str(output_directory)])

    assert result.exit_code == 0
    assert output_file.exists()
    with open(TEST_DATA_DIR / "nhk.xml", "rb") as f:
        assert output_file.read_bytes() == f.read()


def test_cli_calls_extract_function_once_with_input_filename(tmp_path: Path):
    runner = CliRunner()
    input_file = tmp_path / "input.exi"
    input_file.touch(exist_ok=False)

    with patch("btonic.btonic.extract_files") as extract_func:
        runner.invoke(btonic.main, [str(input_file), "-o", str(tmp_path)])

    extract_func.assert_called_once()
    assert extract_func.call_args.args[0] == str(input_file)


@pytest.mark.parametrize(
    "files",
    [
        [],
        [("file1.xml", b"")],
        [("file1.xml", b""), ("file2.xml", b"data")],
        [("file1.xml", b""), ("file2.xml", b"data"), ("FILE", b"\x00\xFF")],
    ],
)
def test_cli_correctly_writes_files_to_output_directory(files, tmp_path: Path):
    runner = CliRunner()
    input_file = tmp_path / "input.exi"
    input_file.touch()
    output_directory = tmp_path / "out"
    output_directory.mkdir(exist_ok=False)
    mock_file_objects = [Mock(filename=filename, data=data) for filename, data in files]

    with patch(
        "btonic.btonic.extract_files", return_value=mock_file_objects,
    ):
        result = runner.invoke(
            btonic.main, [str(input_file), "-o", str(output_directory)]
        )

    assert result.exit_code == 0
    for obj in mock_file_objects:
        assert (output_directory / obj.filename).read_bytes() == obj.data


def test_cli_fails_if_extracted_file_already_exists_in_output_directory(
    tmp_path: Path,
):
    runner = CliRunner()
    input_file = tmp_path / "input.exi"
    input_file.touch()
    output_directory = tmp_path / "out"
    output_directory.mkdir(exist_ok=False)
    output_file = output_directory / "file.xml"
    output_file.touch()

    with patch(
        "btonic.btonic.extract_files",
        return_value=Mock(filename=output_file.name, data=b""),
    ):
        result = runner.invoke(
            btonic.main, [str(input_file), "-o", str(output_directory)]
        )

    assert result.exit_code != 0
