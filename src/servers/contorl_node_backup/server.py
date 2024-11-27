""" Backup server for the control node. This server is responsible for storing the file table and the backup files.

TODO:
- Rather than transmitting the entire file table, only transmit the changes to the file table.
- Implement the backup to DATABASE
"""

import os
import json
from pathlib import Path
import sys
import signal
import grpc
import logging
from concurrent import futures

import backup_master_pb2 as backup_pb2
import backup_master_pb2_grpc as backup_pb2_grpc


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
BACKUP_LOCATION = "~/deeds.backup"


def set_backup_location(location):
    global BACKUP_LOCATION
    BACKUP_LOCATION = location
    os.makedirs(Path(BACKUP_LOCATION).parent, exist_ok=True)
    logging.info(f"Base location set to {BACKUP_LOCATION}")


# Load the file table from a file if it exists
def loadFromFile():
    if os.path.isfile(BACKUP_LOCATION):
        logging.info("File found")
        with open(BACKUP_LOCATION, 'r') as f:
            return json.load(f)
    logging.info("No file found, starting with an empty file table")
    return {}


# Save the file table to disk
def saveToFile(file_table):
    with open(BACKUP_LOCATION, 'w') as my_json:
        json.dump(file_table, my_json, ensure_ascii=False)
    logging.info("File table saved to disk")


# Signal handler for graceful shutdown
def int_handler(signal, frame):
    saveToFile(BackUpServer.file_table)
    logging.info("Gracefully shutting down server")
    sys.exit(0)


# BackUpServer class implementing the gRPC service
class BackUpServer(backup_pb2_grpc.BackUpServiceServicer):
    file_table = loadFromFile()

    def getFileTable(self, request, context):
        file_table_string = json.dumps(self.file_table)
        logging.info("File table requested")
        return backup_pb2.FileTable(file_table_json=file_table_string)

    def updateFileTable(self, request, context):
        self.file_table = json.loads(request.file_table_json)
        logging.info("File table updated")
        return backup_pb2.Empty()


# Main function to start the server
def serve(address):
    set_backup_location(Path(os.environ.get('DEEDS_BACKUP_LOCATION', BACKUP_LOCATION)).resolve())
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    backup_pb2_grpc.add_BackUpServiceServicer_to_server(BackUpServer(), server)
    server.add_insecure_port(address)
    server.start()
    logging.info("Primary BackUp Server is running")
    signal.signal(signal.SIGINT, int_handler)  # Handle Ctrl+C to shutdown gracefully
    server.wait_for_termination()

if __name__ == "__main__":
    serve('[::]:50051')
