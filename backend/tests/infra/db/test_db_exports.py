import infra.db as db_module


def test_db_module_exports_expected_symbols() -> None:
    assert "Base" in db_module.__all__
    assert "get_session_factory" in db_module.__all__
