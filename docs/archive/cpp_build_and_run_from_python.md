# Build And Run C++ From Python

This guide defines one stable workflow for building and running the C++ bridge (`haruquant`) from Python.

## Why this exists

Two recurring local issues were causing build failures:

1. Generator mismatch in the same build directory  
`build/` may already be configured with a different generator (for example `Ninja`), then a Visual Studio configure fails.

2. `kernel32.lib` (or similar MSVC libs) missing during Ninja reconfigure  
This happens when the shell is not initialized for MSVC toolchain usage.

## Standard workflow (recommended)

The legacy repo-local helper `backend/scripts/build_cpp_bridge.py` was removed during cleanup.

## Build + run C++ logging usage example

This guide is retained as historical context only.

## Optional flags

Legacy helper command examples removed.

## Troubleshooting

### Error: generator does not match previous one

Do not reuse the conflicted build directory.  
Use a clean directory:

Legacy helper command removed.

### Error: cannot open file `kernel32.lib`

Use Visual Studio generator (default in this script) and avoid ad-hoc Ninja configure in an uninitialized shell.

### Python cannot import `haruquant`

Confirm the module exists after build:
- `build/bridge/Release/haruquant*.pyd`

Then run the usage script from project root:

```powershell
python tests/usage/utils/usage_cpp_logger.py
```
