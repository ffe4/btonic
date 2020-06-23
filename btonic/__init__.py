import click

from btonic.btonic import convert

__version__ = "0.1.0"
__all__ = ["convert"]


@click.command()
@click.argument("file", type=click.File("rb"))
@click.argument("output", type=click.File("wb"))
def main(file, output):
    output.write(convert(file))


if __name__ == "__main__":
    main()
