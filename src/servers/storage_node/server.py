import os
import grpc
import logging
import minion_pb2
import minion_pb2_grpc
from concurrent import futures

# Configure logging
logging.basicConfig(level=logging.DEBUG if os.getenv("DEBUG_MODE", "false").lower() == "true" else logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# Check if debug mode is enabled via environment variable
debug_Mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Get DATA_DIR from environment variable or default to a home directory path
DATA_DIR = os.getenv("GFS_DATA_DIR", os.path.expanduser("~") + "/gfs_root/")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logger.info(f"Created data directory at {DATA_DIR}")


class MinionService(minion_pb2_grpc.MinionServiceServicer):
    class Chunks:
        blocks = {}

        def put(self, block_uuid, data, minions):
            block_addr = os.path.join(DATA_DIR, str(block_uuid))
            with open(block_addr, 'w') as f:
                f.write(data)
            logger.info(f"Stored block {block_uuid} at {block_addr}")

            # If there are more minions, forward the data
            if len(minions) > 0:
                self.forward(block_uuid, data, minions)

        def get(self, block_uuid):
            block_addr = os.path.join(DATA_DIR, str(block_uuid))
            if not os.path.isfile(block_addr):
                logger.warning(f"Block {block_uuid} not found at {block_addr}")
                return None
            with open(block_addr, 'r') as f:
                logger.info(f"Retrieved block {block_uuid} from {block_addr}")
                return f.read()

        def forward(self, block_uuid, data, minions):
            logger.debug(f"Forwarding block {block_uuid} to minions: {minions}")
            minion = minions[0]
            minions = minions[1:]
            host, port = minion

            # Create a gRPC channel and stub to call the next Minion
            with grpc.insecure_channel(f"{host}:{port}") as channel:
                stub = minion_pb2_grpc.MinionServiceStub(channel)
                stub.put(minion_pb2.PutRequest(block_uuid=block_uuid, data=data, minions=[minion_pb2.Minion(host=h, port=p) for h, p in minions]))
            logger.info(f"Forwarded block {block_uuid} to {host}:{port}")

        def _secure_delete(self, path, passes=1):
            with open(path, "ba+") as delfile:
                length = delfile.tell()
            with open(path, "br+") as delfile:
                for i in range(passes):
                    delfile.seek(0)
                    delfile.write(os.urandom(length))
            os.remove(path)

        def delete_block(self, block_uuid):
            block_addr = os.path.join(DATA_DIR, str(block_uuid))
            if not os.path.isfile(block_addr):
                logger.warning(f"Attempted to delete non-existent block {block_uuid} at {block_addr}")
                return minion_pb2.DeleteResponse(success=False)
            # os.remove(block_addr)
            self._secure_delete(block_addr)
            logger.info(f"Deleted block {block_uuid} from {block_addr}")
            return minion_pb2.DeleteResponse(success=True)

    def put(self, request, context):
        block_uuid = request.block_uuid
        data = request.data
        minions = [(m.host, m.port) for m in request.minions]
        logger.debug(f"Received put request for block {block_uuid} with data size {len(data)} and minions {minions}")
        self.Chunks().put(block_uuid, data, minions)
        return minion_pb2.Empty()

    def get(self, request, context):
        block_uuid = request.block_uuid
        logger.debug(f"Received get request for block {block_uuid}")
        data = self.Chunks().get(block_uuid)
        if data is None:
            context.set_details("Block not found.")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return minion_pb2.GetResponse(data="")
        return minion_pb2.GetResponse(data=data)

    def deleteBlock(self, request, context):
        block_uuid = request.block_uuid
        logger.debug(f"Received delete request for block {block_uuid}")
        response = self.Chunks().delete_block(block_uuid)
        return response

    def forward(self, request, context):
        block_uuid = request.block_uuid
        data = request.data
        minions = [(m.host, m.port) for m in request.minions]
        logger.debug(f"Received forward request for block {block_uuid} with data size {len(data)} and minions {minions}")
        self.Chunks().forward(block_uuid, data, minions)
        return minion_pb2.Empty()

# Start the gRPC server
def serve(address):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    minion_pb2_grpc.add_MinionServiceServicer_to_server(MinionService(), server)
    server.add_insecure_port(address)
    server.start()
    logger.info(f"Minion Server running on port {address.split(':')[-1]}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve("[::]:8888")
