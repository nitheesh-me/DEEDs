import json
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


class DEEDSFS(LoggingMixIn, Operations):
    client = None

    def __init__(self):
        address = os.getenv("DEEDS_MASTER_ADDRESS", "localhost:50051")
        self.client = DeedsClient(address)
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
            if stbuf is None:
                raise FuseOSError(errno.ENOENT)
            try:
                return json.loads(stbuf)
            except json.JSONDecodeError:
                raise FuseOSError(errno.ENOENT)
        except Exception as e:
            print(e)
            print(e.__traceback__)
            raise FuseOSError(errno.ENOENT)

    def readdir(self, path, fh):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            yield from self.client.readdir(path, fh)
            # yield from [".", "..", "test.txt"]
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def create(self, path, mode, fi=None):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            # return self.client.create(path, mode)
            response = self.client.create(path, mode)
            if response:
                return 0
            else:
                return -1
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def mkdir(self, path, mode):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            # return self.client.mkdir(path, mode)
            response = self.client.mkdir(path, mode)
            if response:
                return 0
            else:
                return -1
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()
            raise FuseOSError(errno.ENOENT)

    def unlink(self, path):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            response = self.client.unlink(path)
            if response:
                return 0
            else:
                return -1
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def rmdir(self, path):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            response = self.client.rmdir(path)
            if response:
                return 0
            else:
                return -1
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def rename(self, old, new):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(old)
        try:
            response = self.client.rename(old, new)
            if response:
                return 0
            else:
                return -1
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def open(self, path, flags):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            return 0
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def read(self, path, size, offset, fh):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            r_content = self.client.read(path, size, offset, fh)
            return r_content
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def write(self, path, data, offset, fh):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            return self.client.write(path, data, offset, fh)
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def truncate(self, path, length, fh=None):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            return self.client.truncate(path, length, fh)
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def release(self, path, fh):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            return self.client.release(path, fh)
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)

    def statfs(self, path):
        if not self.has_mounted or not self.client:
            raise fuse.FuseOSError(errno.ENOENT)
        if not self.client:
            self.init(path)
        try:
            return self.client.statfs(path)
        except Exception as e:
            print(e)
            raise FuseOSError(errno.ENOENT)




"""
Test with

```bash
touch test.txt
> init, getattr

ls .
> access, getattr

touch test2.txt
mkdir testdir

ls testdir

df -hT /mnt/deeds/

cp test.txt testdir/

echo "Hello, DEEDSFS!" > test.txt
"""