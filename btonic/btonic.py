import click


@click.command()
@click.argument("file", type=click.File("rb"))
@click.argument("output", type=click.File("wb"))
def main(file, output):
    output.write(convert(file))


def convert(file):
    raise NotImplementedError()
