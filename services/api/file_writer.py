"""Episode-relative, atomic file mutations. On Windows parent handles prevent path swaps."""
from __future__ import annotations
import contextlib
import ctypes
import json
import os
import re
import stat
import threading
import time
import uuid
from pathlib import Path,PureWindowsPath

class UnsafePath(ValueError):pass

_locks={}
_locks_guard=threading.Lock()
_depths=threading.local()

def no_links(path:Path):
    for item in [path,*path.parents]:
        if item.exists() or item.is_symlink():
            info=item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                raise UnsafePath('Symlinks, junctions and reparse points are prohibited: '+str(item))
            if item.is_file() and info.st_nlink>1:
                raise UnsafePath('Hard-linked production files are prohibited')

def assert_clean_tree(root):
    """Reject pre-existing aliases before OS execution; MXC denies creating external hardlinks."""
    root=Path(root);no_links(root)
    stack=[root]
    while stack:
        directory=stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                # DirEntry.stat on Windows may omit the hard-link count (0); lstat queries it.
                try:info=os.lstat(entry.path)
                except FileNotFoundError:continue # an atomically replaced temporary file vanished
                if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                    raise UnsafePath('Reparse point in episode workspace: '+entry.path)
                if stat.S_ISREG(info.st_mode) and info.st_nlink>1:
                    raise UnsafePath('Hard link in episode workspace: '+entry.path)
                if stat.S_ISDIR(info.st_mode):stack.append(Path(entry.path))

@contextlib.contextmanager
def parent_handles(path:Path):
    """Hold every existing ancestor without FILE_SHARE_DELETE, checked as reparse-point handles."""
    handles=[]
    if os.name!='nt':
        no_links(path)
        yield
        return
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE]
    kernel.CreateFileW.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    kernel.GetFileAttributesW.argtypes=[w.LPCWSTR];kernel.GetFileAttributesW.restype=w.DWORD
    try:
        for item in reversed(path.parents):
            if not item.exists():continue
            handle=kernel.CreateFileW(str(item),0x80,0x1|0x2,None,3,0x02000000|0x00200000,None)
            if handle==ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
            # OPEN_REPARSE_POINT opens the link itself; parent handle prevents rename/replacement.
            attributes=kernel.GetFileAttributesW(str(item))
            if attributes==0xffffffff or attributes&0x400:raise UnsafePath('Reparse-point ancestor rejected')
        no_links(path)
        yield
    finally:
        for handle in reversed(handles):kernel.CloseHandle(handle)

class EpisodeWriter:
    def __init__(self,root):
        self.root=Path(root).absolute()
        no_links(self.root)
        if not self.root.is_dir():raise UnsafePath('Episode root is not a directory')

    def path(self,relative, *, immutable=False):
        value=str(relative)
        win=PureWindowsPath(value)
        parts=value.replace('\\','/').split('/')
        if win.is_absolute() or win.drive or value.startswith(('/','\\')) or any(p in ('','..','.') for p in parts):
            raise UnsafePath('Output paths must be episode-relative descendants, without traversal')
        if any(':' in p or p.endswith((' ','.')) or re.search(r'[\x00-\x1f<>"|?*]',p) or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?',p,re.I) for p in parts):
            raise UnsafePath('Invalid or device output filename')
        if not immutable and (value.replace('\\','/')=='.production/input_snapshot' or value.replace('\\','/').startswith('.production/input_snapshot/') or value.replace('\\','/')=='.production/provenance.json'):
            raise UnsafePath('Immutable input snapshots may only be written during trusted bootstrap')
        path=self.root.joinpath(*parts)
        no_links(path)
        if not path.resolve(strict=False).is_relative_to(self.root.resolve()):raise UnsafePath('Destination escapes episode root')
        return path

    def bytes(self,relative,content, *, immutable=False,replace=True):
        path=self.path(relative,immutable=immutable)
        # Create descendants one at a time, rechecking ancestors and holding their handles.
        current=self.root
        for part in path.parent.relative_to(self.root).parts:
            child=current/part
            with parent_handles(child):child.mkdir(exist_ok=True)
            no_links(child);current=child
        with parent_handles(path):
            if path.exists() and (immutable or not replace):raise UnsafePath('Refusing to overwrite immutable/existing file')
            temporary=path.parent/('.w-'+uuid.uuid4().hex[:16]+'.tmp')
            try:
                fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_BINARY if os.name=='nt' else os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as handle:
                    handle.write(content);handle.flush();os.fsync(handle.fileno())
                self.path(relative,immutable=immutable) # immediate open-time/replacement recheck
                # Windows refuses to replace a file another thread/process (dashboard poll, AV, indexer)
                # momentarily holds open; retry briefly instead of failing the whole job.
                for attempt in range(40):
                    try:os.replace(temporary,path);break
                    except PermissionError:
                        if attempt==39:raise
                        time.sleep(.05*min(attempt+1,6))
            finally:temporary.unlink(missing_ok=True)
        return path

    def text(self,relative,content,**kwargs):return self.bytes(relative,content.encode('utf-8'),**kwargs)
    def json(self,relative,content,**kwargs):return self.text(relative,json.dumps(content,ensure_ascii=False,indent=2)+'\n',**kwargs)
    def delete(self,relative):
        path=self.path(relative)
        with parent_handles(path):
            if path.is_dir():raise UnsafePath('Recursive directory deletion is not a production operation')
            path.unlink()
    def rename(self,source,dest):
        a=self.path(source);b=self.path(dest)
        with parent_handles(a),parent_handles(b):os.replace(a,b)

@contextlib.contextmanager
def episode_lock(root,name='mutation',blocking=True):
    root=Path(root)
    key=(str(root),name)
    with _locks_guard:lock=_locks.setdefault(key,threading.RLock())
    if not lock.acquire(blocking=blocking):raise UnsafePath('Conflicting episode operation is already running')
    held=getattr(_depths,'held',{})
    _depths.held=held
    if key in held:
        held[key]+=1
        try:yield
        finally:held[key]-=1;lock.release()
        return
    held[key]=1;handle=None;locked=False
    try:
        writer=EpisodeWriter(root);path=writer.path(f'.production/locks/{name}.lock');path.parent.mkdir(parents=True,exist_ok=True)
        handle=path.open('a+b')
        if os.name=='nt':
            import msvcrt
            handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|(0 if blocking else fcntl.LOCK_NB))
        locked=True
        yield
    finally:
        if handle and locked and os.name=='nt':
            try:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            except OSError:pass
        if handle:handle.close()
        held.pop(key,None);lock.release()
