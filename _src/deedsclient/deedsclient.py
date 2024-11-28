import stat, time, os, errno, fuse

from .datatypes import _dummy_attrs, Chunk, ChunkLocation, FileMetadata, FolderMetadata, GFSMetadata, FileAttrs


class ControlNode:
    def __init__(self):
        now = int(time.time())
        self.fd = 0
        self.gfs_metadata = GFSMetadata(
            files={
                '/': FolderMetadata(
                    folder_name='/',
                    last_access_time=now,
                    last_modified_time=now,
                    attrs=FileAttrs(
                        st_mode=stat.S_IFDIR | 0o755,
                        st_nlink=2,
                        st_size=0,
                        st_atime=now,
                        st_mtime=now,
                        st_ctime=now,
                        st_uid=0,
                        st_gid=0,
                        st_blksize=64 * 1024 * 1024,
                        st_blocks=1,
                        st_ino=0,
                        st_dev=0,
                    ),
                    files=['hello.txt'],
                    folders=[]
                ),
                '/hello.txt': FileMetadata(
                    file_name='/hello.txt',
                    file_size=13,
                    last_access_time=now,
                    last_modified_time=now,
                    chunk_ids=['chunk_001'],
                    chunk_locations=[
                        ChunkLocation(chunk_id='chunk_001', chunk_server='server_1', replication_index=0),
                        ChunkLocation(chunk_id='chunk_001', chunk_server='server_2', replication_index=1),
                        ChunkLocation(chunk_id='chunk_001', chunk_server='server_3', replication_index=2)
                    ],
                    attrs=FileAttrs(
                        st_mode=stat.S_IFREG | 0o644,
                        st_nlink=1,
                        st_size=13,
                        st_atime=now,
                        st_mtime=now,
                        st_ctime=now,
                        st_uid=0,
                        st_gid=0,
                        st_blksize=64 * 1024 * 1024,
                        st_blocks=1,
                        st_ino=0,
                        st_dev=0,
                    )
                )
            },
            chunks={},
            chunk_servers=[
                'server_1',
                'server_2',
                'server_3'
            ],
            file_version_map={},
            total_storage_capacity=1000000000,  # 1 GB
            total_used_space=0,
            start_time=now
        )

    def get_metadata(self, path):
        try:
            return self.gfs_metadata.files[path]
        except KeyError:
            raise FileNotFoundError

    def chmod(self, path, mode):
        self.gfs_metadata.files[path].attrs.st_mode &= 0o770000
        self.gfs_metadata.files[path].attrs.st_mode |= mode
        return 0

    def chown(self, path, uid, gid):
        self.gfs_metadata.files[path].attrs.st_uid = uid
        self.gfs_metadata.files[path].attrs.st_gid = gid
        return 0

    def create(self, path, mode, uid=0, gid=0):
        now = int(time.time())
        chunk_id = sn1.add_chunk()
        sn2.add_chunk(chunk_id)
        sn3.add_chunk(chunk_id)
        self.gfs_metadata.files[path] = FileMetadata(
            file_name=path,
            file_size=0,
            last_access_time=now,
            last_modified_time=now,
            chunk_ids=[chunk_id],
            chunk_locations=[
                ChunkLocation(chunk_id=chunk_id, chunk_server='server_1', replication_index=0),
                ChunkLocation(chunk_id=chunk_id, chunk_server='server_2', replication_index=1),
                ChunkLocation(chunk_id=chunk_id, chunk_server='server_3', replication_index=2)
            ],
            attrs=FileAttrs(
                st_mode=stat.S_IFREG | mode,
                st_nlink=1,
                st_size=0,
                st_atime=now,
                st_mtime=now,
                st_ctime=now,
                st_uid=uid,
                st_gid=gid,
                st_blksize=64 * 1024 * 1024,
                st_blocks=1,
                st_ino=0,
                st_dev=0,
            )
        )
        self.__add_file_to_parent_folder(path)
        return 0
        self.fd += 1
        return self.fd

    def mkdir(self, path, mode):
        now = int(time.time())
        self.gfs_metadata.files[path] = FolderMetadata(
            folder_name=path,
            last_access_time=now,
            last_modified_time=now,
            attrs=FileAttrs(
                st_mode=stat.S_IFDIR | mode,
                st_nlink=2,
                st_size=0,
                st_atime=now,
                st_mtime=now,
                st_ctime=now,
                st_uid=0,
                st_gid=0,
                st_blksize=64 * 1024 * 1024,
                st_blocks=1,
                st_ino=0,
                st_dev=0,
            ),
            files=[],
            folders=[]
        )
        self.__add_file_to_parent_folder(path)
        return 0

    def unlink(self, path):
        chunk_ids = self.gfs_metadata.files[path].chunk_ids
        for chunk_id in chunk_ids:
            sn1.remove_chunk(chunk_id)
            sn2.remove_chunk(chunk_id)
            sn3.remove_chunk(chunk_id)
        del self.gfs_metadata.files[path]
        return 0

    def __add_file_to_parent_folder(self, path):
        parent_folder = os.path.dirname(path)
        if parent_folder in self.gfs_metadata.files:
            self.gfs_metadata.files[parent_folder].files.append(os.path.basename(path))


class StorageNode:
    LOCATION = '/home/'
    start = 1
    chunk_prefix = 'chunk_'

    def __init__(self, location):
        self.chunks = [
            # 'chunk_001'
            self.chunk_prefix + str(self.start).zfill(3)
        ]
        self.LOCATION += location
        os.makedirs(self.LOCATION, exist_ok=True)

    def read(self, chunk_id, size, offset):
        if chunk_id not in self.chunks:
            raise FileNotFoundError
        with open(f"{self.LOCATION}{chunk_id}", 'rb') as f:
            f.seek(offset)
            data = f.read(size)
        return data

    def write(self, chunk_id, data, offset):
        if chunk_id not in self.chunks:
            raise FileNotFoundError
        with open(f"{self.LOCATION}{chunk_id}", 'wb') as f:
            f.seek(offset)
            return f.write(data)

    def add_chunk(self, chunk_id=None):
        if chunk_id:
            self.chunks.append(chunk_id)
            return chunk_id
        self.start += 1
        chunk_id = self.chunk_prefix + str(self.start).zfill(3)
        self.chunks.append(chunk_id)
        return chunk_id

    def remove_chunk(self, chunk_id):
        self.chunks.remove(chunk_id)
        os.remove(f"{self.LOCATION}{chunk_id}")
        return 0


cn = ControlNode()
sn1 = StorageNode("server_1/")
# write `Hello, DEEDSFS!` to chunk_001
sn1.write('chunk_001', b'Hello, DEEDSFS!\n\r', 0)
sn2 = StorageNode("server_2/")
sn3 = StorageNode("server_3/")


class DeedsClient:
    def __init__(self):
        self.cn = cn
        self.sn1 = sn1
        self.sn2 = sn2
        self.sn3 = sn3

    @property
    def files(self):
        return self.cn.gfs_metadata.files

    def chmod(self, path, mode):
        return self.cn.chmod(path, mode)

    def chown(self, path, uid, gid):
        return self.cn.chown(path, uid, gid)

    def create(self, path, mode, uid=0, gid=0):
        return self.cn.create(path, mode, uid, gid)

    def mkdir(self, path, mode):
        return self.cn.mkdir(path, mode)

    def unlink(self, path):
        return self.cn.unlink(path)

    def getattr(self, path, fh=None):
        if path not in self.files:
            raise fuse.FuseOSError(errno.ENOENT)
        try:
            return self.cn.get_metadata(path).attrs.serialize()
        except FileNotFoundError:
            return _dummy_attrs(path)
        except Exception as e:
            print(e)
            return _dummy_attrs(path)

    def list_directory(self, path):
        path_metadata = self.cn.get_metadata(path)
        if type(path_metadata) is FolderMetadata:
            yield from ['.', '..']
            yield from path_metadata.folders
            yield from path_metadata.files
        else:
            raise fuse.FuseOSError(errno.ENOTDIR)

    def open(self, path, flags):
        """Safety? read / write / execute / delete"""
        if path not in self.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return 0

    def read(self, path, size, offset, fh):
        if path not in self.files:
            raise fuse.FuseOSError(errno.ENOENT)
        file_metadata = self.cn.get_metadata(path)
        if type(file_metadata) is not FileMetadata:
            raise fuse.FuseOSError(errno.EISDIR)
        # Get the chunk ids of the file
        print(f"Reading file {path}")
        print(file_metadata)
        chunk_ids = file_metadata.chunk_ids
        # Read the data from offset based on the size
        data = b''
        for i, chunk_id in enumerate(chunk_ids):
            print(f"Reading chunk {chunk_id} with size {size} and offset {offset}")
            # skip to offset
            if offset > 0:
                offset -= file_metadata.attrs.st_blksize
                continue
            # of out of size break
            if size <= 0:
                break

            data += sn1.read(chunk_id, size, offset)
            size -= len(data)
        return data

    def write(self, path, data, offset, fh):
        if path not in self.files:
            raise fuse.FuseOSError(errno.ENOENT)
        file_metadata = self.cn.get_metadata(path)
        if type(file_metadata) is not FileMetadata:
            raise fuse.FuseOSError(errno.EISDIR)
        # Get the chunk ids of the file
        chunk_ids = file_metadata.chunk_ids
        # Write the data to the chunk
        for i, chunk_id in enumerate(chunk_ids):
            # skip to offset
            if offset > file_metadata.attrs.st_size:
                offset -= file_metadata.attrs.st_blksize
                continue
            # of out of size break
            if len(data) <= 0:
                break

            print(f"Writing chunk {chunk_id}")
            write_len = sn1.write(chunk_id, data, offset)
            break
        # update size in control
        self.cn.gfs_metadata.files[path].attrs.st_size -= offset - write_len
        return len(data)

    def close(self, path, fh):
        pass
