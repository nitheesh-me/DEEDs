import click
from .deedsfs import DEEDSFS
from .deedsclient import DeedsClient

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

@deedsctl.command()
@click.option('--ttl', default=60, help='The time-to-live for the file.')
@click.argument('path')
def expire(ttl, path):
    """Set the time-to-live for a file."""
    import os
    address = os.getenv("DEEDS_MASTER_ADDRESS", "localhost:50051")
    client = DeedsClient(address)
    click.echo(f"Setting time-to-live for {path} to {ttl}...")
    client.reset_expire(path, ttl)


if __name__ == '__main__':
    deedsctl()
