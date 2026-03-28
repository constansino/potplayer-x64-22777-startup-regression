# Email Draft

Subject: PotPlayer x64 `1.7.22777` startup regression in `PotPlayer64.dll`

To: `ir@kakaocorp.com`, `hotline@kakaocorp.com`, `jebo@kakaocorp.com`, `esg@kakaocorp.com`, `k.safety@kakaocorp.com`, `jeju@kakaocorp.com`, `conv@kakaocorp.com`, `careers@kakaocorp.com`, `bestir@kakaocorp.com`

Hello Kakao team,

I am reporting a reproducible startup regression in PotPlayer x64.

- Fast version: `PotPlayer64.dll 1.7.22775.0`
- Slow version: `PotPlayer64.dll 1.7.22777.0`
- `PotPlayerMini64.exe` is unchanged between the two installs
- Both DLLs are officially signed by Kakao Corp.

Measured result on Windows x64:

- `1.7.22777.0`: first visible main window in about `9.2s` to `9.6s`
- `1.7.22775.0`: first visible main window in about `0.65s` to `0.85s`

I isolated the issue by swapping only `PotPlayer64.dll` in the same install directory:

- baseline `22777`: `9510 ms`
- swap only to `22775`: `771 ms`
- restore `22777`: `9626 ms`

This points directly to a regression in `PotPlayer64.dll 1.7.22777.0`.

I also sampled the hot startup thread. In the slow build, it stays for several seconds inside the virtualized `.themida` region of `PotPlayer64.dll`, around module offset `+0x1C1F2AE`, before the first window appears. The fast build passes through the protected region quickly and reaches normal GUI initialization.

Public report:

- Repository: `REPO_URL`
- PR / report URL: `PR_URL`

Could you please route this to the PotPlayer x64 engineering / release team and check whether `1.7.22777.0` introduced a protected-loader startup regression?

Thank you.
