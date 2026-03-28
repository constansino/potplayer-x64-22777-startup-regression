import argparse
import ctypes as ct
import subprocess
import time
from ctypes import wintypes as wt
from pathlib import Path

import pefile
import psutil


kernel32 = ct.WinDLL("kernel32", use_last_error=True)
psapi = ct.WinDLL("psapi", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
THREAD_SUSPEND_RESUME = 0x0002
THREAD_GET_CONTEXT = 0x0008
THREAD_QUERY_INFORMATION = 0x0040
LIST_MODULES_ALL = 0x03
CONTEXT_AMD64 = 0x100000
CONTEXT_CONTROL = CONTEXT_AMD64 | 0x1


class M128A(ct.Structure):
    _fields_ = [("Low", ct.c_ulonglong), ("High", ct.c_longlong)]


class XMM_SAVE_AREA32(ct.Structure):
    _fields_ = [
        ("ControlWord", wt.WORD),
        ("StatusWord", wt.WORD),
        ("TagWord", wt.BYTE),
        ("Reserved1", wt.BYTE),
        ("ErrorOpcode", wt.WORD),
        ("ErrorOffset", wt.DWORD),
        ("ErrorSelector", wt.WORD),
        ("Reserved2", wt.WORD),
        ("DataOffset", wt.DWORD),
        ("DataSelector", wt.WORD),
        ("Reserved3", wt.WORD),
        ("MxCsr", wt.DWORD),
        ("MxCsr_Mask", wt.DWORD),
        ("FloatRegisters", M128A * 8),
        ("XmmRegisters", M128A * 16),
        ("Reserved4", wt.BYTE * 96),
    ]


class CONTEXT(ct.Structure):
    _fields_ = [
        ("P1Home", ct.c_ulonglong),
        ("P2Home", ct.c_ulonglong),
        ("P3Home", ct.c_ulonglong),
        ("P4Home", ct.c_ulonglong),
        ("P5Home", ct.c_ulonglong),
        ("P6Home", ct.c_ulonglong),
        ("ContextFlags", wt.DWORD),
        ("MxCsr", wt.DWORD),
        ("SegCs", wt.WORD),
        ("SegDs", wt.WORD),
        ("SegEs", wt.WORD),
        ("SegFs", wt.WORD),
        ("SegGs", wt.WORD),
        ("SegSs", wt.WORD),
        ("EFlags", wt.DWORD),
        ("Dr0", ct.c_ulonglong),
        ("Dr1", ct.c_ulonglong),
        ("Dr2", ct.c_ulonglong),
        ("Dr3", ct.c_ulonglong),
        ("Dr6", ct.c_ulonglong),
        ("Dr7", ct.c_ulonglong),
        ("Rax", ct.c_ulonglong),
        ("Rcx", ct.c_ulonglong),
        ("Rdx", ct.c_ulonglong),
        ("Rbx", ct.c_ulonglong),
        ("Rsp", ct.c_ulonglong),
        ("Rbp", ct.c_ulonglong),
        ("Rsi", ct.c_ulonglong),
        ("Rdi", ct.c_ulonglong),
        ("R8", ct.c_ulonglong),
        ("R9", ct.c_ulonglong),
        ("R10", ct.c_ulonglong),
        ("R11", ct.c_ulonglong),
        ("R12", ct.c_ulonglong),
        ("R13", ct.c_ulonglong),
        ("R14", ct.c_ulonglong),
        ("R15", ct.c_ulonglong),
        ("Rip", ct.c_ulonglong),
        ("FltSave", XMM_SAVE_AREA32),
        ("VectorRegister", M128A * 26),
        ("VectorControl", ct.c_ulonglong),
        ("DebugControl", ct.c_ulonglong),
        ("LastBranchToRip", ct.c_ulonglong),
        ("LastBranchFromRip", ct.c_ulonglong),
        ("LastExceptionToRip", ct.c_ulonglong),
        ("LastExceptionFromRip", ct.c_ulonglong),
    ]


class MODULEINFO(ct.Structure):
    _fields_ = [("lpBaseOfDll", wt.LPVOID), ("SizeOfImage", wt.DWORD), ("EntryPoint", wt.LPVOID)]


EnumProcessModulesEx = psapi.EnumProcessModulesEx
EnumProcessModulesEx.argtypes = [wt.HANDLE, ct.POINTER(wt.HMODULE), wt.DWORD, ct.POINTER(wt.DWORD), wt.DWORD]
GetModuleFileNameExW = psapi.GetModuleFileNameExW
GetModuleFileNameExW.argtypes = [wt.HANDLE, wt.HMODULE, wt.LPWSTR, wt.DWORD]
GetModuleInformation = psapi.GetModuleInformation
GetModuleInformation.argtypes = [wt.HANDLE, wt.HMODULE, ct.POINTER(MODULEINFO), wt.DWORD]
OpenProcess = kernel32.OpenProcess
OpenThread = kernel32.OpenThread
SuspendThread = kernel32.SuspendThread
ResumeThread = kernel32.ResumeThread
GetThreadContext = kernel32.GetThreadContext
CloseHandle = kernel32.CloseHandle


def get_modules(pid: int) -> list[tuple[int, int, str]]:
    handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        raise OSError(ct.get_last_error())
    try:
        needed = wt.DWORD()
        modules = (wt.HMODULE * 1024)()
        if not EnumProcessModulesEx(handle, modules, ct.sizeof(modules), ct.byref(needed), LIST_MODULES_ALL):
            raise OSError(ct.get_last_error())
        count = needed.value // ct.sizeof(wt.HMODULE)
        result = []
        for idx in range(count):
            info = MODULEINFO()
            GetModuleInformation(handle, modules[idx], ct.byref(info), ct.sizeof(info))
            buf = ct.create_unicode_buffer(32768)
            GetModuleFileNameExW(handle, modules[idx], buf, len(buf))
            base = ct.cast(info.lpBaseOfDll, ct.c_void_p).value
            result.append((base, base + info.SizeOfImage, buf.value))
        return result
    finally:
        CloseHandle(handle)


def sample_rip(tid: int) -> int | None:
    handle = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, False, tid)
    if not handle:
        return None
    try:
        if SuspendThread(handle) == 0xFFFFFFFF:
            return None
        ctx = CONTEXT()
        ctx.ContextFlags = CONTEXT_CONTROL
        ok = GetThreadContext(handle, ct.byref(ctx))
        ResumeThread(handle)
        if not ok:
            return None
        return ctx.Rip
    finally:
        CloseHandle(handle)


def map_addr(addr: int, modules: list[tuple[int, int, str]]) -> tuple[str | None, int | None]:
    for start, end, path in modules:
        if start <= addr < end:
            return path, addr - start
    return None, None


def section_name(pe_path: str, module_offset: int | None) -> str | None:
    if module_offset is None:
        return None
    pe = pefile.PE(pe_path, fast_load=False)
    for section in pe.sections:
        start = section.VirtualAddress
        end = start + max(section.Misc_VirtualSize, section.SizeOfRawData)
        if start <= module_offset < end:
            return section.Name.rstrip(b"\x00").decode(errors="ignore")
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, help="Path to PotPlayerMini64.exe")
    parser.add_argument("--sample-seconds", type=float, default=6.0)
    args = parser.parse_args()

    proc = subprocess.Popen([args.exe])
    process = psutil.Process(proc.pid)
    try:
        modules = get_modules(proc.pid)
        previous = {t.id: t.user_time + t.system_time for t in process.threads()}
        started = time.perf_counter()
        while time.perf_counter() - started < args.sample_seconds:
            current = {t.id: t.user_time + t.system_time for t in process.threads()}
            deltas = [(tid, current[tid] - previous.get(tid, current[tid])) for tid in current]
            deltas.sort(key=lambda item: item[1], reverse=True)
            hot_tid, hot_delta = deltas[0]
            rip = sample_rip(hot_tid)
            mod_path, mod_offset = map_addr(rip, modules) if rip else (None, None)
            name = section_name(mod_path, mod_offset) if mod_path else None
            now_ms = round((time.perf_counter() - started) * 1000)
            print(
                {
                    "t_ms": now_ms,
                    "tid": hot_tid,
                    "cpu_delta_s": round(hot_delta, 4),
                    "rip": hex(rip) if rip else None,
                    "module": mod_path,
                    "module_offset": hex(mod_offset) if mod_offset is not None else None,
                    "section": name,
                }
            )
            previous = current
            time.sleep(0.1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
