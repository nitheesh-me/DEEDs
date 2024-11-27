from dataclasses import dataclass
import functools
import logging
import random
import configparser
import grpc
from concurrent import futures

import master_pb2
import master_pb2_grpc
import minion_pb2
import minion_pb2_grpc


NODE_MAP = {
    #  A:storage1:50051,B:storage2:50051,C:storage3:50051
    "A": "storage1:50051",
    "B": "storage2:50051",
    "C": "storage3:50051",
}


class DeedsClient:
    def __init__(self, address):
        self.address = address
        self.channel = grpc.insecure_channel(address)
        self.master_stub = master_pb2_grpc.MasterServiceStub(self.channel)
        self.test()

    def _get_minion_stub(self, host, port=None):
        if port is None:
            channel = grpc.insecure_channel(host)
        else:
            channel = grpc.insecure_channel(f"{host}:{port}")
        return minion_pb2_grpc.MinionServiceStub(channel)

    def _list_files(self):
        yield from self.master_stub.getListOfFiles(master_pb2.Location(path="/")).files

    def create(self, fname, mode):
        request = master_pb2.Location(path=str(fname), mode=mode)
        response = self.master_stub.create(request)
        return response

    def getattr(self, fname, fh):
        request = master_pb2.GetFileTableEntryRequest(fname=fname)
        response = self.master_stub.getFileTableEntry(request)
        return response.attrs

    def getxattr(self, path, name, position=0):
        ...     # TODO

    def listxattr(self, path):
        ...     # TODO

    def setxattr(self, path, name, value, options, position=0):
        ...     # TODO

    def removexattr(self, path, name):
        ...     # TODO

    def rename(self, old, new):
        ...     # TODO

    def open(self, fname, flags):
        ...     # TODO

    def read(self, path, size, offset, fh):
        ...     # TODO

    def write(self, path, data, offset, fh):
        ...     # TODO

    def readdir(self, path, fh):
        yield from [".", ".."]
        yield from self._list_files()

    def mkdir(self, path, mode):
        request = master_pb2.Location(path=str(path), mode=mode)
        response = self.master_stub.mkdir(request)
        return response

    def rmdir(self, path):
        ...     # TODO

    def truncate(self, fname, length, fh=None):
        ...     # TODO

    def unlink(self, fname):
        ...     # TODO

    def release(self, fname, fh):
        ...     # TODO

    def statfs(self, path):
        ...     # TODO



    def test(self):
        channel = grpc.insecure_channel(target=self.address)
        master_stub = master_pb2_grpc.MasterServiceStub(channel)

        # put a file
        print("Putting a file")
        file_details = master_pb2.WriteRequest(dest="/test.txt", size=9)
        blocks = master_stub.write(file_details).blocks
        print(f"Blocks: {blocks}")
        block_size = master_stub.getBlockSize(master_pb2.Empty()).size
        print(f"Block size: {block_size}")
        for block in blocks:
            minion = NODE_MAP[block.node_id]
            minion_stub = self._get_minion_stub(minion)
            put_request = minion_pb2.PutRequest(block_uuid=block.block_uuid, data=b"Hello Tim", minions=[])
            put_response = minion_stub.put(put_request)
            print(f"Put response: {put_response}")

        minions = master_stub.getMinions(master_pb2.Empty()).minions
        print(f"Minions: {minions}")

        # get a file
        print("Getting a file")
        file_details = master_pb2.GetFileTableEntryRequest(fname="/test.txt")
        file_details = master_stub.getFileTableEntry(file_details)
        print(f"File details: {file_details}")

        # read a file
        print("Reading a file")
        read_request = master_pb2.ReadRequest(fname="/test.txt")
        read_response = master_stub.read(read_request)
        print(f"Read response: {read_response}")
        for block in read_response.blocks:
            minion = NODE_MAP[block.node_id]
            minion_stub = self._get_minion_stub(minion)
            get_request = minion_pb2.GetRequest(block_uuid=block.block_uuid)
            get_response = minion_stub.get(get_request)
            print(f"Get response: {get_response}")

        # Get the list of files
        print("List of files:")
        for file in self._list_files():
            print(file)

        # delete a file
        # print("Deleting a file")
        # delete_request = master_pb2.DeleteRequest(fname="test.txt")
        # delete_response = master_stub.delete(delete_request)
        # print(f"Delete response: {delete_response}")

        # # list files
        # print("List of files:")
        # for file in self.list_files():
        #     print(file)
        print("Test complete")
