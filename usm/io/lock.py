from pathlib import Path
from filelock import FileLock
from usm.settings import get_usm_home

class USMLock:
    def __init__(self, timeout: int = 15):
        self.lock_file = get_usm_home() / "usm.lock"
        self.lock = FileLock(str(self.lock_file), timeout=timeout)

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
