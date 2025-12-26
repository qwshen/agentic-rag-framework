import time

def nvl(a, b):
    return a if a is not None else b

def is_file_ready(file_path: str):
    ready: bool = False
    while not ready:
        time.sleep(0.6)
        try:
            with open(file_path, 'ab') as f:
                ready = True
        except (IOError, PermissionError):
            return False
    return ready
