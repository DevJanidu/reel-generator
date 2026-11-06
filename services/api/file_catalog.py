"""Read-only public episode directory metadata; never traverse private job state."""
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from .file_writer import no_links, UnsafePath


def public_catalog(root: Path):
    root = Path(root)
    no_links(root)
    result = []
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.name.lower() == '.production' or entry.name.endswith('.tmp'):
                    continue
                path = Path(entry.path)
                try:
                    info = path.lstat()
                    no_links(path)
                except FileNotFoundError:
                    continue  # An atomic write completed during this read.
                if stat.S_ISDIR(info.st_mode):
                    kind, size = 'directory', None
                    stack.append(path)
                elif stat.S_ISREG(info.st_mode):
                    kind, size = 'file', info.st_size
                else:
                    raise UnsafePath('Unsupported entry in episode file catalog')
                result.append(dict(path=path.relative_to(root).as_posix(), kind=kind,
                                   size_bytes=size, modified_at=datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat()))
    return sorted(result, key=lambda item: item['path'].casefold())
