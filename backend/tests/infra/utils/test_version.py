from pathlib import Path

import infra.utils.version as version_module


def test_get_version_reads_root_version_file(monkeypatch) -> None:
    fake_path = Path(__file__).resolve().parents[3]
    monkeypatch.setattr(version_module, "__file__", str(fake_path / "src" / "infra" / "utils" / "version.py"))

    assert version_module.get_version() == "1.0.0"
