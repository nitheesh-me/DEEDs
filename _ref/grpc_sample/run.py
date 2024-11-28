"""
+-------------------+       gRPC       +-------------------+
|                   | <--------------> |                   |
|   gRPC Client     |   Bidirectional  |   gRPC Server     |
|                   |   Communication  |                   |
+-------------------+                  +-------------------+

python -m grpc_tools.protoc \
    -I. \
    --include_imports
    --python_out=. \
    --grpc_python_out=. \
    --proto_path=. \
    ./sample.proto
"""
import multiprocessing

from run_server import serve as server
from run_client import run as client


def run():
    server_process = multiprocessing.Process(target=server)
    server_process.start()

    client_process = multiprocessing.Process(target=client)
    client_process.start()

    server_process.join()
    client_process.join()


if __name__ == '__main__':
    run()