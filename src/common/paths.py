from pathlib import Path


def find_project_root(start: Path = Path(__file__).parent) -> Path:
    for parent in start.resolve().parents:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Project root not found")


BASE_DIR = find_project_root()
