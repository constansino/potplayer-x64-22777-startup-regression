import argparse
import ctypes as ct
import subprocess
import time
from ctypes import wintypes as wt


user32 = ct.WinDLL("user32", use_last_error=True)
EnumWindows = user32.EnumWindows
EnumWindows.argtypes = [ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM), wt.LPARAM]
EnumWindows.restype = wt.BOOL
IsWindowVisible = user32.IsWindowVisible
IsWindowVisible.argtypes = [wt.HWND]
IsWindowVisible.restype = wt.BOOL
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
GetWindowThreadProcessId.restype = wt.DWORD


def has_visible_window(pid: int) -> bool:
    found = []

    @ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def callback(hwnd, _lparam):
        procid = wt.DWORD()
        GetWindowThreadProcessId(hwnd, ct.byref(procid))
        if procid.value == pid and IsWindowVisible(hwnd):
            found.append(hwnd)
            return False
        return True

    EnumWindows(callback, 0)
    return bool(found)


def bench_once(exe: str, timeout: float) -> int | None:
    proc = subprocess.Popen([exe])
    start = time.perf_counter()
    elapsed_ms = None
    try:
        while time.perf_counter() - start < timeout:
            if has_visible_window(proc.pid):
                elapsed_ms = round((time.perf_counter() - start) * 1000)
                break
            time.sleep(0.03)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
    return elapsed_ms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True, help="Path to PotPlayerMini64.exe")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()

    values = [bench_once(args.exe, args.timeout) for _ in range(args.runs)]
    print(values)


if __name__ == "__main__":
    main()
