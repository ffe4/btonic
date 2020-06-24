from pathlib import Path

import click

from btonic.btonic_file import extract_files


@click.command()
@click.argument(
    "file", type=click.Path(dir_okay=False, exists=True, readable=True),
)
@click.option(
    "-o",
    "--output",
    "output_directory",
    default=".",
    type=click.Path(file_okay=False, exists=True, writable=True),
    help="Directory to which files should be written.",
)
def main(file, output_directory):
    for outfile in extract_files(file):
        path = Path(output_directory) / outfile.filename
        if path.exists():
            raise FileExistsError
        with open(path, "wb") as f:
            f.write(outfile.data)
