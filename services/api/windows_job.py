"""Kill a native worker and all descendants if its trusted controller exits."""
import ctypes,os
from ctypes import wintypes as w

class ProcessJob:
    def __init__(self,process):
        if os.name!='nt':raise OSError('Windows Job Objects are required')
        class Basic(ctypes.Structure):
            _fields_=[('per_process',ctypes.c_longlong),('per_job',ctypes.c_longlong),('flags',w.DWORD),('min_ws',ctypes.c_size_t),('max_ws',ctypes.c_size_t),('active',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(ctypes.Structure):_fields_=[(name,ctypes.c_ulonglong) for name in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.argtypes=[w.LPVOID,w.LPCWSTR];kernel.CreateJobObjectW.restype=w.HANDLE
        kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD]
        kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        kernel.CloseHandle.argtypes=[w.HANDLE]
        self.kernel=kernel;self.handle=kernel.CreateJobObjectW(None,None)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        limits=Extended();limits.basic.flags=0x2000 # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(self.handle,w.HANDLE(int(process._handle))):
            error=ctypes.WinError(ctypes.get_last_error());self.close();raise error
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None
