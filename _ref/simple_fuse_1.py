import os
import sys
import fuse
from fuse import FUSE, Operations

class SimpleFS(Operations):
    def __init__(self):
        # Initialize the file system with a single file
        self.files = {
            '/hello.txt': {
                'content': b'Hello, world!',
                'size': 13
            }
        }

    def getattr(self, path):
        """ Get the file attributes for a file at `path` """
        if path == '/':
            return {
                'st_mode': (fuse.S_IFDIR | 0o755),
                'st_nlink': 2
            }
        elif path == '/hello.txt':
            return {
                'st_mode': (fuse.S_IFREG | 0o644),
                'st_size': self.files[path]['size'],
                'st_nlink': 1
            }
        else:
            raise fuse.FuseOSError(fuse.ENOENT)

    def readdir(self, path, fh):
        """ List directory contents """
        if path == '/':
            return ['.', '..', 'hello.txt']
        else:
            raise fuse.FuseOSError(fuse.ENOENT)

    def read(self, path, size, offset, fh):
        """ Read the content of a file """
        if path == '/hello.txt':
            content = self.files[path]['content']
            return content[offset:offset + size]
        else:
            raise fuse.FuseOSError(fuse.ENOENT)

def main(mountpoint):
    # Mount the filesystem at the specified mount point
    FUSE(SimpleFS(), mountpoint, foreground=True)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: %s <mountpoint>' % sys.argv[0])
        sys.exit(1)

    mountpoint = sys.argv[1]
    main(mountpoint)
