import use_cases.component as component_use_cases


def test_component_use_case_exports() -> None:
    assert "CreateComponentUseCase" in component_use_cases.__all__
    assert component_use_cases.DeleteComponentUseCase is not None
