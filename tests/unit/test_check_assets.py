import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "check_assets", Path(__file__).parents[2] / "scripts" / "check_assets.py"
)
mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(mod)  # type: ignore[union-attr]


def test_unlisted_asset_is_reported(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "avatar.glb").write_text("x")
    (tmp_path / "ASSETS.md").write_text("# Assets\n")
    assert mod.missing_assets(tmp_path) == ["assets/avatar.glb"]


def test_listed_asset_passes(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "avatar.glb").write_text("x")
    (tmp_path / "ASSETS.md").write_text("| assets/avatar.glb | CC0 | url |\n")
    assert mod.missing_assets(tmp_path) == []
