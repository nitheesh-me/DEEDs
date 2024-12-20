import os
import stat
from time import time
import uuid
import math
import random
import configparser
import signal
import sys
import json
import grpc
import logging
from concurrent import futures

import master_pb2
import master_pb2_grpc

import backup_master_pb2
import backup_master_pb2_grpc

import minion_pb2
import minion_pb2_grpc
import redis


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

DEEDS_BACKUP_ADDR = os.environ.get("DEEDS_BACKUP_ADDR", "backup:50051")
TTL = 30

# Handle graceful shutdown
def int_handler(signal, frame):
    try:
        con = grpc.insecure_channel(DEEDS_BACKUP_ADDR)
        stub = backup_master_pb2_grpc.BackUpServiceStub(con)
        content = MasterService.Master.file_table
        file_table_string = json.dumps(content)
        stub.updateFileTable(backup_master_pb2.FileTable(file_table_json=file_table_string))
    except grpc.RpcError as e:
        logging.error("Primary backup Server not found: %s", e)
        logging.error("Master Server memory lost")
    sys.exit(0)

# Read configuration from the config file
def set_conf():
    conf = configparser.ConfigParser()
    try:
        conf.read('GFS.conf')
    except Exception as e:
        logging.error("Error reading configuration file: %s", e)
        sys.exit(1)
    MasterService.Master.block_size = int(conf.get('master', 'block_size'))
    global TTL
    TTL = int(conf.get('master', 'ttl') or TTL)
    minions = conf.get('master', 'chunkServers').split(',')

    for m in minions:
        id, host, port = m.split(":")
        MasterService.Master.minions[id] = f"{host}:{port}"

    try:
        con = grpc.insecure_channel(DEEDS_BACKUP_ADDR)
        stub = backup_master_pb2_grpc.BackUpServiceStub(con)
        file_table_backup = stub.getFileTable(backup_master_pb2.Empty())
        MasterService.Master.file_table = json.loads(file_table_backup.file_table_json)
    except grpc.RpcError as e:
        logging.error("Primary backup Server not found: %s", e)
        logging.error("Start the primary_backup_server")


class FileExpireHandler:
    def __init__(self):
        self.redis_conn = redis.Redis(host='redis', port=6379, db=0)
        self.pubsub = self.redis_conn.pubsub()
        self.pubsub.psubscribe(**{"__keyevent@0__:expired": self.event_handler})
        self.pubsub.run_in_thread(sleep_time=0.01)

    def event_handler(self, message):
        logging.info(f"Received message: {message}")
        try:
            key = message["data"].decode("utf-8")
            logging.info(f"Received message: {message}")
            if key in MasterService.Master.file_table:
                MasterService.Master.delete(key)
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    def add_key(self, key, ttl):
        self.redis_conn.setex(key, ttl, 1)

    def remove_key(self, key):
        self.redis_conn.delete(key)

    def reset_expire(self, key, ttl):
        if self.redis_conn.exists(key):
            if ttl == 0:
                self.redis_conn.delete(key)
            if ttl < 0:
                self.redis_conn.persist(key)
            self.redis_conn.expire(key, ttl)


class ChunkManager:
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

    def delete_chunk(self, deletion_blocks):
        logging.info(f"Deleting blocks: {deletion_blocks}")
        for (block_uuid, node_id, block_index) in deletion_blocks:
            minion = MasterService.Master.minions[node_id]
            minion_stub = self._get_minion_stub(minion)
            delete_request = minion_pb2.DeleteRequest(block_uuid=block_uuid)
            delete_response = minion_stub.deleteBlock(delete_request)
            logging.info(f"Delete response: {delete_response}")


# Implement the MasterService class
class MasterService(master_pb2_grpc.MasterServiceServicer):
    expire_handler = FileExpireHandler()
    class Master:
        file_attributes = {}
        file_table = {}
        minions = {}
        # locks = {}
        block_size = 0

        @staticmethod
        def read(fname):
            return MasterService.Master.file_table[fname]

        @staticmethod
        def write(dest, size):
            if dest in MasterService.Master.file_table:
                pass
            else:
                MasterService.Master.create(dest, 0o644)

            num_blocks = MasterService.Master.calc_num_blocks(size)
            blocks = MasterService.Master.alloc_blocks(dest, num_blocks, size)
            now = int(time())
            MasterService.Master.file_attributes[dest].update({
                "st_size": size,
                "st_mtime": now,
                "st_blocks": num_blocks,
                "st_blksize": MasterService.Master.block_size,

            })
            return blocks

        @staticmethod
        def mkdir(dest, mode=0o755):
            if dest in MasterService.Master.file_table:
                return None
            MasterService.Master.file_table[dest] = []
            now = int(time())
            MasterService.Master.file_attributes[dest] = {
                "st_mode": stat.S_IFDIR | mode,
                "st_nlink": 1,      # Need to implement this with reference counting
                "st_uid": 0,
                "st_gid": 0,
                "st_size": 0,
                "st_atime": now,
                "st_mtime": now,
                "st_ctime": now,
                "st_blocks": 0,
                "st_blksize": 0,
                "st_ino": 0,
                "st_dev": 0,
                "files": set(),
                "folders": set()
            }
            # add the directory to the parent directory
            if not dest == "/":
                MasterService.Master.file_attributes[os.path.dirname(dest)]["folders"].add(os.path.basename(dest))
                MasterService.expire_handler.add_key(dest, TTL)
            parent_dir = dest
            while parent_dir != "/":
                parent_dir = os.path.dirname(dest)
                MasterService.Master.file_attributes[parent_dir]["st_nlink"] += 1
                dest = parent_dir

            return dest

        @staticmethod
        def create(fname, mode):
            if fname in MasterService.Master.file_table:
                return None
            MasterService.Master.file_table[fname] = []
            now = int(time())
            MasterService.Master.file_attributes[fname] = {
                "st_mode": stat.S_IFREG | mode,
                "st_nlink": 1,
                "st_uid": 0,
                "st_gid": 0,
                "st_size": 0,
                "st_atime": now,
                "st_mtime": now,
                "st_ctime": now,
                "st_blocks": 0,
                "st_blksize": 0,
                "st_ino": 0,
                "st_dev": 0,
            }
            MasterService.expire_handler.add_key(fname, TTL)
            MasterService.Master._link_add(fname)


        @staticmethod
        def _link_add(fname):
            # add the file to the parent directory
            parent_dir = os.path.dirname(fname)
            MasterService.Master.file_attributes[parent_dir]["files"].add(os.path.basename(fname))
            orig_ = fname
            parent_dir = fname
            while parent_dir != "/":
                parent_dir = os.path.dirname(fname)
                MasterService.Master.file_attributes[parent_dir]["st_nlink"] += 1
                fname = parent_dir
                MasterService.expire_handler.reset_expire(parent_dir, TTL)
            return orig_

        @staticmethod
        def _link_delete(fname):
            parent_dir = os.path.dirname(fname)
            MasterService.expire_handler.remove_key(fname)
            MasterService.Master.file_attributes[parent_dir]["st_nlink"] -= 1
            logging.info(f"Parent dir: {parent_dir}")
            logging.info(f"File attributes: {MasterService.Master.file_attributes[parent_dir]}")
            if os.path.basename(fname) in MasterService.Master.file_attributes[parent_dir]["files"]:
                MasterService.Master.file_attributes[parent_dir]["files"].remove(os.path.basename(fname))
            else:
                MasterService.Master.file_attributes[parent_dir]["folders"].remove(os.path.basename(fname))
            if MasterService.Master.file_attributes[parent_dir]["st_nlink"] == 0 and parent_dir != "/":
                MasterService.Master.delete(parent_dir)
                MasterService.Master._link_delete(parent_dir)

        @staticmethod
        def delete(fname):
            if fname not in MasterService.Master.file_table:
                return None

            # Delete the chunk
            if fname in MasterService.Master.file_table:
                deletion_blocks = MasterService.Master.file_table[fname]
                ChunkManager().delete_chunk(deletion_blocks)
            if MasterService.Master.file_attributes[fname]["st_mode"] == stat.S_IFDIR:
                for file in MasterService.Master.file_attributes[fname]["files"]:
                    MasterService.Master.delete(os.path.join(fname, file))
                for folder in MasterService.Master.file_attributes[fname]["folders"]:
                    MasterService.Master.delete(os.path.join(fname, folder))
            MasterService.Master._link_delete(fname)
            MasterService.Master.file_attributes.pop(fname)
            return MasterService.Master.file_table.pop(fname, None)

        @staticmethod
        def rename(src, dest):
            if src not in MasterService.Master.file_table:
                return None
            MasterService.Master.file_table[dest] = MasterService.Master.file_table.pop(src)
            MasterService.Master.file_attributes[dest] = MasterService.Master.file_attributes.pop(src)
            MasterService.Master._link_add(dest)
            MasterService.Master._link_delete(src)
            return dest

        @staticmethod
        def getFileTableEntry(fname):
            return MasterService.Master.file_table.get(fname, None)

        @staticmethod
        def getFileAttributes(fname):
            return MasterService.Master.file_attributes.get(fname, None)

        @staticmethod
        def getListOfFiles(path="/"):
            if path not in MasterService.Master.file_table:
                return []
            folders = MasterService.Master.file_attributes[path]["folders"]
            files = MasterService.Master.file_attributes[path]["files"]
            return list(folders) + list(files)

        @staticmethod
        def getBlockSize():
            return MasterService.Master.block_size

        @staticmethod
        def getMinions():
            return MasterService.Master.minions

        @staticmethod
        def calc_num_blocks(size):
            return int(math.ceil(float(size) / MasterService.Master.block_size))


        @staticmethod
        def alloc_blocks(dest, num, size=0):
            blocks = MasterService.Master.file_table[dest]
            _blocks = [
                master_pb2.Block(block_uuid=block_uuid, node_id=nodes_id, block_index=block_index)
                for (block_uuid, nodes_id, block_index) in blocks
            ]
            for i in range(len(blocks), num):
                block_uuid = str(uuid.uuid1())
                nodes_id = random.choice(list(MasterService.Master.minions.keys()))
                _blocks.append(master_pb2.Block(block_uuid=block_uuid, node_id=nodes_id, block_index=i))

                MasterService.Master.file_table[dest].append((block_uuid, nodes_id, i))
            # Remove extra blocks if file size is reduced
            deletion_blocks = []
            if num < len(blocks):
                for i in range(num, len(blocks)):
                    block_uuid, nodes_id, block_index = MasterService.Master.file_table[dest].pop()
                    deletion_blocks.append(_blocks.pop())
                    ChunkManager().delete_chunk(deletion_blocks)
            return _blocks

    def __init__(self):
        """Adds root directory to the file table"""
        super().__init__()
        if "/" not in MasterService.Master.file_table:
            MasterService.Master.mkdir("/")
            logging.info("Root directory created")

    # Implement the gRPC service methods
    def statfs(self, request, context):
        total_blocks = sum([len(x) for x in MasterService.Master.file_table.values()])
        free_blocks = 10*3 - total_blocks
        block_size = MasterService.Master.block_size
        total_files = sum([len(x.get("files", [])) for x in MasterService.Master.file_attributes.values()])
        free_files = 10 - total_files
        return master_pb2.StatfsResponse(
            total_blocks=total_blocks,
            free_blocks=free_blocks,
            block_size=block_size,
            total_files=total_files,
            free_files=free_files,
        )

    def read(self, request, context):
        mapping = MasterService.Master.read(request.fname)
        mapping_blocks = list(map(lambda x: master_pb2.Block(block_uuid=x[0], node_id=x[1], block_index=x[2]), mapping))
        return master_pb2.FileMapping(blocks=mapping_blocks)

    def create(self, request, context):
        dest = MasterService.Master.create(request.path, request.mode)
        return master_pb2.Location(path=dest)

    def mkdir(self, request, context):
        dest = MasterService.Master.mkdir(request.path, request.mode)
        return master_pb2.Location(path=dest)

    def rename(self, request, context):
        src = request.src
        dest = request.dest
        if src not in MasterService.Master.file_table:
            return master_pb2.Empty()
        MasterService.Master.file_table[dest] = MasterService.Master.file_table.pop(src)
        MasterService.Master.file_attributes[dest] = MasterService.Master.file_attributes.pop(src)
        MasterService.Master.file_attributes[os.path.dirname(dest)]["files"].add(os.path.basename(dest))
        return master_pb2.Empty()

    def write(self, request, context):
        blocks = MasterService.Master.write(request.dest, request.size)
        return master_pb2.BlockList(blocks=blocks)

    def delete(self, request, context):
        mapping_to_delete = MasterService.Master.delete(request.fname)
        if mapping_to_delete is None:
            return master_pb2.FileMapping(blocks=[])
        blocks = list(map(lambda x: master_pb2.Block(block_uuid=x[0], node_id=x[1], block_index=x[2]), mapping_to_delete))
        return master_pb2.FileMapping(blocks=blocks)

    def getFileTableEntry(self, request, context):
        file_entry = MasterService.Master.getFileTableEntry(request.fname)
        if file_entry is None:
            logging.warning(f"File {request.fname} not found")
            logging.info(f"File table: {MasterService.Master.file_table}")
            return master_pb2.FileMapping(blocks=[])
        file_block_list = list(map(lambda x: master_pb2.Block(block_uuid=x[0], node_id=x[1], block_index=x[2]), file_entry))
        file_attributes = MasterService.Master.getFileAttributes(request.fname)
        logging.info(f"File {request.fname} found")

        return master_pb2.FileMapping(
            attrs=json.dumps(file_attributes, cls=SetEncoder),
            blocks=file_block_list
        )

    def getListOfFiles(self, request, context):
        file_list = MasterService.Master.getListOfFiles(request.path)
        return master_pb2.FileList(files=file_list)

    def getBlockSize(self, request, context):
        block_size = MasterService.Master.getBlockSize()
        return master_pb2.BlockSize(size=block_size)

    def getMinions(self, request, context):
        minions = MasterService.Master.getMinions()
        logging.info(f"Minions: {minions}")
        return master_pb2.MinionList(minions=minions)

    def setExpireTime(self, request, context):
        MasterService.expire_handler.reset_expire(request.fname, request.ttl)
        return master_pb2.Empty()


def serve(address):
    set_conf()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    master_pb2_grpc.add_MasterServiceServicer_to_server(MasterService(), server)
    server.add_insecure_port(address)
    server.start()
    logging.info("Master Server running")
    signal.signal(signal.SIGINT, int_handler)  # Handle Ctrl+C to shutdown gracefully
    server.wait_for_termination()


if __name__ == "__main__":
    serve('[::]:50051')
