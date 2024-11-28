from dataclasses import dataclass
from typing import List, Dict, Optional


def _dummy_attrs(path):
    return {
        'st_mode': 33188,
        'st_ino': 2,
        'st_dev': 16777220,
        'st_nlink': 1,
        'st_uid': 501,
        'st_gid': 20,
        'st_size': 13,
        'st_atime': 1631081167,
        'st_mtime': 1631081167,
        'st_ctime': 1631081167,
        'st_blksize': 4096,
        'st_blocks': 8
    }

@dataclass
class Chunk:
    """Represents a chunk of data stored in the system."""
    chunk_id: str               # Unique identifier for the chunk (e.g., hash of file data)
    size: int                   # Size of the chunk in bytes
    replication_factor: int     # Number of replicas
    last_modified_time: int     # Last modification time (in seconds since epoch)

    def __post_init__(self):
        if self.size <= 0:
            raise ValueError("Chunk size must be greater than 0.")
        if self.replication_factor < 1:
            raise ValueError("Replication factor must be at least 1.")

@dataclass
class ChunkLocation:
    """Represents a chunk's location across different machines (servers)."""
    chunk_id: str           # Unique chunk identifier
    chunk_server: str       # Name/ID of the server storing the chunk
    replication_index: int  # Index of this replica (e.g., first, second, etc.)

    def __post_init__(self):
        if self.replication_index < 0:
            raise ValueError("Replication index must be non-negative.")

@dataclass
class FileAttrs:
    """Represents statistics for a file in the GFS. """
    # `stats = os.stat(file_path)`
    st_mode: int        # Specifies the mode of the file. This includes file type information
    st_ino: int         # The file serial number, which distinguishes this file from all other files on the same device.
    st_dev: int         # Identifies the device containing the file. The st_ino and st_dev, taken together, uniquely identify the file. The st_dev value is not necessarily consistent across reboots or system crashes, however.
    st_nlink: int       # The number of hard links to the file. This count keeps track of how many directories have entries for this file. If the count is ever decremented to zero, then the file itself is discarded as soon as no process still holds it open. Symbolic links are not counted in the total.
    st_uid: int         # The user ID of the file's owner.
    st_gid: int         # The group ID of the file.
    st_size: int        # The size of the file in bytes.
    st_atime: int       # The time of last access (in seconds since epoch)
    st_mtime: int       # The time of last modification (in seconds since epoch)
    st_ctime: int       # The time of last status change (in seconds since epoch)
    st_blocks: int      # The number of blocks allocated for the file
    st_blksize: int     # The optimal block size for I/O operations
    st_atime_usec: int = 0  # Microsecond component of the last access time
    st_mtime_usec: int = 0  # Microsecond component of the last modification time
    st_ctime_usec: int = 0  # Microsecond component of the last status change time
    # other attributes...
    others: Dict[str, int] | None = None

    # dict
    def serialize(self) -> Dict[str, int]:
        return {
            'st_mode': self.st_mode,
            'st_ino': self.st_ino,
            'st_dev': self.st_dev,
            'st_nlink': self.st_nlink,
            'st_uid': self.st_uid,
            'st_gid': self.st_gid,
            'st_size': self.st_size,
            'st_atime': self.st_atime,
            'st_mtime': self.st_mtime,
            'st_ctime': self.st_ctime,
            'st_blocks': self.st_blocks,
            'st_blksize': self.st_blksize,
            'st_atime_usec': self.st_atime_usec,
            'st_mtime_usec': self.st_mtime_usec,
            'st_ctime_usec': self.st_ctime_usec,
            'others': self.others if self.others else {}
        }


@dataclass
class FileMetadata:
    """Represents a file in the GFS."""
    file_name: str                  # Name of the file
    file_size: int                  # Total size of the file in bytes
    last_access_time: int           # Last access time (in seconds since epoch)
    last_modified_time: int         # Last modification time (in seconds since epoch)
    chunk_ids: List[str]            # List of chunk IDs that represent the file
    chunk_locations: List[ChunkLocation]    # List of chunk locations
    attrs: FileAttrs
    block_size: int = 64 * 1024 * 1024      # Default block size (64 MB)
    num_chunks: int = 0             # Number of chunks the file is split into
    replication_factor: int = 3     # Default replication factor for chunks

    def __post_init__(self):
        if self.file_size < 0:
            raise ValueError("File size must be non-negative.")
        if not self.chunk_ids:
            self.chunk_ids = ['chunk_' + str(i + 1).zfill(3) for i in range(self.num_chunks)]
        self.num_chunks = len(self.chunk_ids)

@dataclass
class FolderMetadata:
    """Represents a folder in the GFS."""
    folder_name: str                # Name of the folder
    last_access_time: int           # Last access time (in seconds since epoch)
    last_modified_time: int         # Last modification time (in seconds since epoch)
    attrs: FileAttrs
    files: List[str]           # List of file names in the folder
    folders: List[str]         # List of subfolder names in the folder
    parent_folder: str | None = None  # Name of the parent folder

    def __post_init__(self):
        if not self.folder_name:
            raise ValueError("Folder name must be provided.")

@dataclass
class GFSMetadata:
    """Represents the metadata stored in the GFS master node."""
    files: Dict[str, FileMetadata | FolderMetadata]        # A dictionary mapping file names to their metadata
    chunks: Dict[str, Chunk]              # A dictionary mapping chunk IDs to their metadata
    chunk_servers: List[str]              # List of available chunk servers in the system
    file_version_map: Dict[str, int]      # Map of file versions (file_name -> version)
    total_storage_capacity: int           # Total storage capacity across all chunk servers
    total_used_space: int                 # Total space used in the system
    start_time: int                       # Start time of the GFS master (e.g., boot time)

    def __post_init__(self):
        if not self.chunk_servers:
            raise ValueError("At least one chunk server must be available.")
        if not self.files:
            raise ValueError("There must be at least one file in the system.")

    def get_free_space(self) -> int:
        """Returns the free storage space across all chunk servers."""
        return self.total_storage_capacity - self.total_used_space

    def get_file(self, file_name: str) -> Optional[FileMetadata]:
        """Retrieves file metadata by its name."""
        return self.files.get(file_name)

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Retrieves chunk metadata by its ID."""
        return self.chunks.get(chunk_id)

    def add_file(self, file_metadata: FileMetadata):
        """Adds a file to the GFS metadata and updates storage usage."""
        if file_metadata.file_name in self.files:
            raise ValueError(f"File {file_metadata.file_name} already exists.")
        self.files[file_metadata.file_name] = file_metadata
        for chunk_id in file_metadata.chunk_ids:
            chunk_metadata = self.chunks.get(chunk_id)
            if chunk_metadata:
                self.total_used_space += chunk_metadata.size
        self.file_version_map[file_metadata.file_name] = 1  # Initialize version for new files

    def remove_file(self, file_name: str):
        """Removes a file from the GFS metadata and updates storage usage."""
        file_metadata = self.files.pop(file_name, None)
        if file_metadata:
            for chunk_id in file_metadata.chunk_ids:
                chunk_metadata = self.chunks.get(chunk_id)
                if chunk_metadata:
                    self.total_used_space -= chunk_metadata.size
            del self.file_version_map[file_name]

    def increment_file_version(self, file_name: str):
        """Increments the version of a file when it is updated."""
        if file_name not in self.file_version_map:
            raise ValueError(f"File {file_name} does not exist.")
        self.file_version_map[file_name] += 1