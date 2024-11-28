import click
from .deedsfs import DEEDSFS

@click.group()
def deedsctl():
    """A command-line tool for DEEDS."""
    pass

@deedsctl.command()
@click.option('--mountpoint', default='/tmp/deedsfs', help='The mountpoint for the DEEDS filesystem.')
def setup(mountpoint):
    """Setup the deedsctl."""
    deedsfs = DEEDSFS()
    click.echo(f"Mouting DEEDS filesystem at {mountpoint}...")
    deedsfs.mount(mountpoint)

if __name__ == '__main__':
    deedsctl()
