# Build And Run C++ From Python

This guide defines one stable workflow for building and running the C++ bridge (`hqt_engine`) from Python.

## Why this exists

Two recurring local issues were causing build failures:

1. Generator mismatch in the same build directory  
`build/` may already be configured with a different generator (for example `Ninja`), then a Visual Studio configure fails.

2. `kernel32.lib` (or similar MSVC libs) missing during Ninja reconfigure  
This happens when the shell is not initialized for MSVC toolchain usage.

## Standard workflow (recommended)

Use the dedicated script:

```powershell
python scripts/build_cpp_bridge.py
```

What it does:
- Configures CMake in a separate directory: `build_vs/`
- Uses Visual Studio generator by default
- Builds only target `hqt_engine`
- Copies built module to `build/bridge/Release/` so Python usage scripts can import it

## Build + run C++ logging usage example

```powershell
python scripts/build_cpp_bridge.py --run-usage
```

This runs:
- `tests/usage/utils/usage_cpp_logger.py`

## Optional flags

```powershell
python scripts/build_cpp_bridge.py --config Debug
python scripts/build_cpp_bridge.py --build-dir build_vs_custom
python scripts/build_cpp_bridge.py --generator "Visual Studio 18 2026" --arch x64
```

## Troubleshooting

### Error: generator does not match previous one

Do not reuse the conflicted build directory.  
Use a dedicated directory:

```powershell
python scripts/build_cpp_bridge.py --build-dir build_vs
```

### Error: cannot open file `kernel32.lib`

Use Visual Studio generator (default in this script) and avoid ad-hoc Ninja configure in an uninitialized shell.

### Python cannot import `hqt_engine`

Confirm the module exists after build:
- `build/bridge/Release/hqt_engine*.pyd`

Then run the usage script from project root:

```powershell
python tests/usage/utils/usage_cpp_logger.py
```

