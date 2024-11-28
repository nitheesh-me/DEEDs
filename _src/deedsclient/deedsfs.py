import os
from functools import wraps
import stat
import sys
import errno
import fuse
import time
from fuse import FUSE, Operations, FuseOSError, fuse_exit, LoggingMixIn

from .deedsclient import DeedsClient


def logger_d(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args: {args} and kwargs: {kwargs}")
        ret = func(*args, **kwargs)
        print(f"Returned {ret}")
        return ret
    return wrapper


class DEEDSFS(Operations):
    client = None

    def __init__(self):
        self.client = DeedsClient()
        self._mountpoint = None
        self._fuse = None
        self.follow_symlinks = True
        self.deedfs_fstat_workaround = False
        self.fd = 0


    @property
    def has_mounted(self):
        return self._mountpoint is not None

    def _run_fuse(self):
        self._fuse = FUSE(
            self,
            self._mountpoint,
            foreground=True,
            # nothreads=True,
        )

    def __call__(self, op, *args):
        if not hasattr(self, op):
            raise FuseOSError(errno.EFAULT)
        f = logger_d(getattr(self, op))
        return f(*args)

    def mount(self, mountpoint):
        self._mountpoint = mountpoint
        # self._fuse_thread = threading.Thread(target=self._run_fuse, daemon=True)
        # self._fuse_thread.start()
        self._run_fuse()

    def unmount(self):
        if self.has_mounted:
            fuse_exit()
            # self._fuse_thread.join(timeout=5)
            self._fuse = None
            self._mountpoint = None

    def init(self, path):
        pass

    def chmod(self, path, mode):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.chmod(path, mode)

    def chown(self, path, uid, gid):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.chown(path, uid, gid)

    def create(self, path, mode, fi=None):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path in self.client.files:
            raise fuse.FuseOSError(errno.EEXIST)
        return self.client.create(path, mode)

    def mkdir(self, path, mode):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path in self.client.files:
            raise fuse.FuseOSError(errno.EEXIST)
        return self.client.mkdir(path, mode)

    def getattr(self, path, fh=None):
        # Mimic the behavior of sshfs_getattr
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            # Placeholder for the logic to get the file's attributes
            # Simulate getting the file attributes as if from SSH
            stbuf = self.client.getattr(path, fh)

            # Return a dictionary like the 'stat' struct
            return stbuf

        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)


    def readdir(self, path, fh):
        """ List directory contents """
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        yield from self.client.list_directory(path)

    def open(self, path, flags):
        """ Open a file """
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.open(path, flags)

    def release(self, path, fh):
        """ Release a file """
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.release(path, fh)


    def read(self, path, size, offset, fh):
        """ Read data from a file """
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        r_content = self.client.read(path, size, offset, fh)
        return r_content

    def write(self, path, data, offset, fh):
        """ Write data to a file """
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.write(path, data, offset, fh)

    def truncate(self, path, length, fh=None):
        """ Truncate a file """
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.truncate(path, length, fh)

    def unlink(self, path):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.unlink(path)

    def rename(self, old, new):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if old not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.rename(old, new)

    def rmdir(self, path):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if path not in self.client.files:
            raise fuse.FuseOSError(errno.ENOENT)
        return self.client.rmdir(path)

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    # def rmdir(self, path):
    #     pass

if __name__ == '__main__':
    mountpoint = sys.argv[1]
    FUSE(DEEDSFS(), mountpoint, foreground=True)
