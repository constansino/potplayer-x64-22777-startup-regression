# PotPlayer x64 1.7.22777 Startup Regression

This repository documents a reproducible startup regression in `PotPlayer64.dll 1.7.22777.0` on Windows x64.

## Summary

- Fast build: `PotPlayer64.dll 1.7.22775.0`
- Slow build: `PotPlayer64.dll 1.7.22777.0`
- Both DLLs are officially signed by Kakao Corp.
- `PotPlayerMini64.exe` stayed the same; swapping only `PotPlayer64.dll` toggled the issue

## Measured Behavior

- `1.7.22777.0`: main window appears in about `9.2s` to `9.6s`
- `1.7.22775.0`: main window appears in about `0.65s` to `0.85s`
- Replacing only `PotPlayer64.dll` in the same install directory changed startup from about `9.5s` to about `0.77s`

## What Was Ruled Out

- User config removal
- Playlist clearing
- Auto-update and browser-related options
- Firewall block
- Local proxy presence
- LAV Filters / madVR integration

These did not materially change startup time.

## Root-Cause Direction

Sampling the hot startup thread shows the slow build spending several seconds inside the virtualized `.themida` region of `PotPlayer64.dll`, while the fast build only passes through the same protected region briefly before entering normal window initialization.

Observed hot location in the slow build:

- Module offset: `PotPlayer64.dll + 0x1C1F2AE`
- Section: `.themida`
- Behavior: the same thread stays pinned around the same RIP for multiple seconds before the first visible window appears

This strongly suggests the regression is in the protected loader / virtualization stage of `1.7.22777.0`, not in PotPlayer user configuration, filters, renderer settings, or networking.

## Environment

- Windows 10 Pro `25H2`
- Build `26200.8039`
- PotPlayer x64

## Reproduction

1. Install PotPlayer x64 with `PotPlayer64.dll 1.7.22777.0`
2. Close all PotPlayer instances
3. Run `scripts/benchmark_startup.py --exe "C:\\Program Files\\DAUM\\PotPlayer\\PotPlayerMini64.exe"`
4. Observe first visible window time around 9 seconds
5. Replace only `PotPlayer64.dll` with the official signed `1.7.22775.0`
6. Run the benchmark again
7. Observe startup drop to sub-1-second range

## Scripts

- `scripts/benchmark_startup.py`
  Measures time to first visible PotPlayer window
- `scripts/sample_hot_thread.py`
  Samples the hottest startup thread and maps its RIP into the target module and PE section

## Practical Workaround

Until Kakao ships a fixed x64 build, pinning `PotPlayer64.dll` back to `1.7.22775.0` is an effective workaround.
