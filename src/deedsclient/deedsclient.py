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
        self.fdid = 0
        self.fd_map = {}

    def _get_minion_stub(self, host, port=None):
        if port is None:
            channel = grpc.insecure_channel(host)
        else:
            channel = grpc.insecure_channel(f"{host}:{port}")
        # wait for the channel to be ready with timeout of 10 seconds
        try:
            grpc.channel_ready_future(channel).result(timeout=10)
        except grpc.FutureTimeoutError:
            raise Exception("Connection to Minion timed out")
        return minion_pb2_grpc.MinionServiceStub(channel)

    def _list_files(self, path="/"):
        yield from self.master_stub.getListOfFiles(master_pb2.Location(path=path)).files

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
        request = master_pb2.RenameRequest(src=str(old), dest=str(new))
        response = self.master_stub.rename(request)
        return response

    def open(self, fname, flags):
        """ What is this?: Open a file, meaning create a file handle, in our case, a file table entry """
        file_details = master_pb2.OpenRequest(fname=fname, flags=flags)
        response = self.master_stub.open(file_details)
        self.fdid += 1
        self.fd_map[self.fdid] = response
        print(f"Opened file {fname} with file handle {self.fdid}")
        return self.fdid

    def read(self, path, size, offset, fh):
        """Stream the output from chunks, considering offset and size"""
        read_request = master_pb2.ReadRequest(fname=path)
        read_response = self.master_stub.read(read_request)
        block_size = self.master_stub.getBlockSize(master_pb2.Empty()).size
        bytes_read = 0

        for block in sorted(read_response.blocks, key=lambda x: x.block_index):
            if offset >= block_size:
                offset -= block_size
                continue

            minion = NODE_MAP[block.node_id]
            minion_stub = self._get_minion_stub(minion)
            get_request = minion_pb2.GetRequest(block_uuid=block.block_uuid)
            get_response = minion_stub.get(get_request)
            data = get_response.data[offset:]
            offset = 0

            while data:
                chunk = data[:size - bytes_read]
                yield chunk
                bytes_read += len(chunk)
                if bytes_read >= size:
                    return
                data = data[len(chunk):]

    def write(self, path, data, offset, fh):
        block_size = self.master_stub.getBlockSize(master_pb2.Empty()).size
        total_file_size = offset + len(data)
        write_request = master_pb2.WriteRequest(fname=path, size=total_file_size)
        write_response = self.master_stub.write(write_request)
        bytes_written = 0

        for block in sorted(write_response.blocks, key=lambda x: x.block_index):
            if offset >= block_size:
                offset -= block_size
                continue

            minion = NODE_MAP[block.node_id]
            minion_stub = self._get_minion_stub(minion)
            put_request = minion_pb2.PutRequest(block_uuid=block.block_uuid, data=data[:block_size - offset])
            put_response = minion_stub.put(put_request)
            data = data[len(put_request.data):]
            bytes_written += len(put_request.data)
            offset = 0

        return bytes_written

    def flush(self, path, fh):
        # Assuming flush is to ensure all data is written to the storage
        if fh not in self.fd_map:
            raise Exception("Invalid file handle")

        file_entry = self.fd_map[fh]
        # Perform any necessary operations to flush data to storage
        # This is a placeholder for actual flush logic
        print(f"Flushing file {path} with file handle {fh}")
        return 0

    def readdir(self, path, fh):
        yield from [".", ".."]
        yield from self._list_files(path)

    def mkdir(self, path, mode):
        request = master_pb2.Location(path=str(path), mode=mode)
        response = self.master_stub.mkdir(request)
        return response

    def rmdir(self, path):
        request = master_pb2.DeleteRequest(fname=str(path))
        response = self.master_stub.delete(request)
        return response

    def truncate(self, fname, length, fh=None):
        ...     # TODO

    def unlink(self, fname):
        request = master_pb2.DeleteRequest(fname=str(fname))
        response = self.master_stub.delete(request)
        return response

    def release(self, fname, fh):
        print(f"Releasing file {fname} with file handle {fh}")
        del self.fd_map[fh]
        return 0

    def statfs(self, path):
        request = master_pb2.Empty()
        response = self.master_stub.statfs(request)
        return dict(f_bsize=response.block_size, f_blocks=response.total_blocks, f_bavail=response.free_blocks)

    def reset_expire(self, path, ttl):
        request = master_pb2.Location(path=path, ttl=ttl)
        response = self.master_stub.setExpireTime(request)
        return response

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
