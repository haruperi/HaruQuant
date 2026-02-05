"""Clean up runner files by removing excessive blank lines and duplicate code."""

import re
from pathlib import Path


def cleanup_file(file_path: Path) -> bool:
    """Clean up a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content

        # Remove duplicate shutdown calls
        content = re.sub(
            r"(\s+# Cleanup\s+mt5_client\.shutdown\(\)\s+)+",
            "\n\n    # Cleanup\n    mt5_client.shutdown()\n",
            content,
        )

        # Remove excessive blank lines (more than 2 consecutive)
        content = re.sub(r"\n\n\n+", "\n\n", content)

        # Remove blank lines between parameter lines in function calls
        # Fix indented parameter blocks with excessive blank lines
        lines = content.split("\n")
        cleaned_lines = []
        in_function_call = False

        for line in lines:
            # Detect if we're entering a function call with parameters
            if re.match(
                r"\s+(account_info|symbol_info|simulator|simulator\.run)\s*=?\s*\w+\(",
                line,
            ):
                in_function_call = True
                cleaned_lines.append(line)
                continue

            # Detect end of function call
            if in_function_call and line.strip() == ")":
                in_function_call = False
                cleaned_lines.append(line)
                continue

            # Inside function call - remove blank lines
            if in_function_call:
                if line.strip() != "":
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)

        content = "\n".join(cleaned_lines)

        # One more pass to remove triple+ blank lines
        content = re.sub(r"\n\n\n+", "\n\n", content)

        if content != original:
            file_path.write_text(content, encoding="utf-8")
            print(f"[OK] Cleaned {file_path.name}")
            return True
        else:
            print(f"[SKIP] No changes for {file_path.name}")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to clean {file_path.name}: {e}")
        return False


def main():
    """Clean up all runner files."""
    files = list(Path("tests/usage/backtest/01_strategies").glob("*_runner.py"))

    print(f"Cleaning {len(files)} runner files")
    print("=" * 70)

    cleaned = 0
    for file_path in sorted(files):
        if cleanup_file(file_path):
            cleaned += 1

    print("=" * 70)
    print(f"Cleaned {cleaned}/{len(files)} files")


if __name__ == "__main__":
    main()
