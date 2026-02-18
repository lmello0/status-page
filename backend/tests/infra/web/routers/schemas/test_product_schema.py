import pytest
from pydantic import ValidationError

from infra.web.routers.schemas.product import ProductResponseDTO, ProductUpdateDTO


def test_product_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="At least one field must be updated"):
        ProductUpdateDTO()


def test_product_update_accepts_partial_payload() -> None:
    dto = ProductUpdateDTO(description="Updated description")

    assert dto.description == "Updated description"
    assert dto.name is None


def test_product_response_serializes_with_camel_case() -> None:
    dto = ProductResponseDTO(
        id=1,
        name="API",
        description="Main API",
        is_visible=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        components=[],
    )

    payload = dto.model_dump(by_alias=True)

    assert "isVisible" in payload
    assert "createdAt" in payload
    assert "updatedAt" in payload
