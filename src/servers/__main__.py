import click

from .contorl_node_backup import backup_server
from .control_node import control_node_server
from .storage_node import storage_node_server


@click.group()
def server():
    pass


@server.command()
@click.option('--address', default='[::]:50051', help='The address to bind to')
def backup(address):
    backup_server(address)


@server.command()
@click.option('--address', default='[::]:50051', help='The address to bind to')
def control(address):
    control_node_server(address)


@server.command()
@click.option('--address', default='[::]:50051', help='The address to bind to')
def storage(address):
    storage_node_server(address)


if __name__ == '__main__':
    server()
