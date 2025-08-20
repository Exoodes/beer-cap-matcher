from pathlib import Path


def test_api_subpackages_have_init() -> None:
    """Ensure every directory under ``src/api`` with Python modules is a package."""
    api_root = Path("src/api")
    missing_init: list[Path] = []
    for path in api_root.rglob("*"):
        if path.is_dir():
            if path.name.startswith(".") or path.name == "__pycache__":
                continue
            if (
                any(f.suffix == ".py" for f in path.rglob("*.py"))
                and not (path / "__init__.py").exists()
            ):
                missing_init.append(path)
    assert (
        not missing_init
    ), f"Missing __init__.py in: {sorted(str(p) for p in missing_init)}"
