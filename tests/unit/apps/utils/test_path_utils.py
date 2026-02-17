import shutil
from pathlib import Path

from apps.utils.data_validator import DataValidator
from apps.utils.path_utils import ensure_dir, ensure_parent_dir, normalize_path


def test_normalize_path_with_base():
    out = normalize_path("reports/output.json", base=Path("data"))
    assert isinstance(out, Path)
    assert out.as_posix().endswith("data/reports/output.json")


def _workspace_tmp() -> Path:
    root = Path("artifacts") / "test_tmp_path_utils"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_ensure_parent_dir_creates_missing_parent():
    file_path = _workspace_tmp() / "nested" / "reports" / "result.json"
    out = ensure_parent_dir(file_path)
    assert out == file_path
    assert file_path.parent.exists()


def test_ensure_dir_creates_directory():
    directory = _workspace_tmp() / "a" / "b" / "c"
    out = ensure_dir(directory)
    assert out == directory
    assert directory.exists()
    assert directory.is_dir()


def test_data_validator_export_report_accepts_path_and_creates_parent():
    validator = DataValidator()
    output_path = _workspace_tmp() / "exports" / "quality" / "report.json"
    validator.export_report(output_path, results={"ok": True}, format="json")
    assert output_path.exists()
