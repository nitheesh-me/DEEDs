import pytest
import os
from deedsclient import DEEDSFS
from icecream import ic

@pytest.fixture(scope="module")
def fs():
    # Initialize and mount the filesystem
    fs = DEEDSFS()
    mount_point = '/tmp/deedsfs' + str(os.getpid())
    os.makedirs(mount_point)
    print("Mounting filesystem...")
    fs.mount(mount_point)
    print("Filesystem mounted.")
    yield fs
    # Unmount and clean up
    fs.unmount()
    os.rmdir(mount_point)

# operations.access(path, amode) -> None
def test_access(fs):
    mountpoint = fs._mountpoint
    file_path = os.path.join(mountpoint, 'test_file.txt')
    with open(file_path, 'w') as f:
        f.write('Hello, DEEDSFS!')
    assert fs.access(file_path, os.F_OK)
    assert True

def test_create_file(fs):
    file_path = os.path.join(fs, 'test_file.txt')
    print(file_path)
    with open(file_path, 'w') as f:
        f.write('Hello, DEEDSFS!')
    assert os.path.exists(file_path)

def test_read_file(fs):
    file_path = os.path.join(fs, 'test_file.txt')
    with open(file_path, 'r') as f:
        content = f.read()
    assert content == 'Hello, DEEDSFS!'

def test_create_file_without_mount():
    file_path = '/tmp/deedsfs' + str(os.getpid()) + '/test_file.txt'
    with open(file_path, 'w') as f:
        f.write('Hello, DEEDSFS!')
    assert not os.path.exists(file_path)

# def test_write_file(fs):
#     file_path = os.path.join(fs, 'test_file.txt')
#     with open(file_path, 'a') as f:
#         f.write(' Testing write operation.')
#     with open(file_path, 'r') as f:
#         content = f.read()
#     assert content == 'Hello, DEEDSFS! Testing write operation.'

# def test_delete_file(fs):
#     file_path = os.path.join(fs, 'test_file.txt')
#     os.remove(file_path)
#     assert not os.path.exists(file_path)

# def test_create_directory(fs):
#     dir_path = os.path.join(fs, 'test_dir')
#     os.mkdir(dir_path)
#     assert os.path.isdir(dir_path)

# def test_list_directory(fs):
#     dir_path = os.path.join(fs, 'test_dir')
#     file_path = os.path.join(dir_path, 'inner_file.txt')
#     with open(file_path, 'w') as f:
#         f.write('Inner file content.')
#     contents = os.listdir(dir_path)
#     assert 'inner_file.txt' in contents

# def test_remove_directory(fs):
#     dir_path = os.path.join(fs, 'test_dir')
#     os.rmdir(dir_path)
#     assert not os.path.exists(dir_path)

# def test_rename_file(fs):
#     old_path = os.path.join(fs, 'old_name.txt')
#     new_path = os.path.join(fs, 'new_name.txt')
#     with open(old_path, 'w') as f:
#         f.write('Rename test.')
#     os.rename(old_path, new_path)
#     assert os.path.exists(new_path)
#     assert not os.path.exists(old_path)

# def test_file_permissions(fs):
#     file_path = os.path.join(fs, 'perm_test.txt')
#     with open(file_path, 'w') as f:
#         f.write('Permission test.')
#     os.chmod(file_path, 0o644)
#     permissions = oct(os.stat(file_path).st_mode & 0o777)
#     assert permissions == '0o644'

# def test_file_attributes(fs):
    file_path = os.path.join(fs, 'attr_test.txt')
    with open(file_path, 'w') as f:
        f.write('Attribute test.')
    stats = os.stat(file_path)
    assert stats.st_size == len('Attribute test.')