# Findings

## Version Split

- Current slow file: `PotPlayer64.dll 1.7.22777.0`
- Fast backup file: `PotPlayer64.dll 1.7.22775.0`
- `PotPlayerMini64.exe` hash matched across both installs
- `PotPlayer64.dll` hash differed
- Both DLLs were signed by `CN=Kakao Corp.`

## Swap Test

Using the same PotPlayer install directory:

- Baseline with `22777`: `9510 ms`
- Swap only to `22775`: `771 ms`
- Restore `22777`: `9626 ms`

This isolates the regression to `PotPlayer64.dll 1.7.22777.0`.

## Startup Timeline

- Slow `22777` build:
  first visible window around `9174 ms`
- Fast `22775` build:
  first visible window around `654 ms`

Network activity to the local proxy happened after the window appeared in the slow build, so startup was not blocked on outbound networking.

## Hot Thread Sampling

During the slow startup period, one thread repeatedly consumed CPU while staying at:

- `PotPlayer64.dll + 0x1C1F2AE`

This offset falls inside the PE section:

- `.themida`

In the fast `22775` build, execution moved through the protected region quickly and reached `win32u.dll` within about `100 ms`, matching normal GUI startup.

## Interpretation

The regression appears to be inside the protected startup path of the x64 DLL:

- virtualized loader
- unpack / decrypt stage
- anti-tamper / protection initialization

This is an inference from timing, thread RIP sampling, section mapping, and the isolated DLL swap test.
