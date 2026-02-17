"""Usage examples for pathlib-based path utilities."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.utils.path_utils import ensure_dir, ensure_parent_dir, normalize_path


def main() -> None:
    print("--- path_utils usage ---")

    normalized = normalize_path("reports/validation.json", base=ROOT / "data")
    print("normalized:", normalized)

    ensured_file = ensure_parent_dir(ROOT / "artifacts" / "reports" / "quality.json")
    print("ensured parent for file:", ensured_file.parent)

    ensured_dir = ensure_dir(ROOT / "artifacts" / "tmp" / "paths")
    print("ensured directory:", ensured_dir)


if __name__ == "__main__":
    main()

