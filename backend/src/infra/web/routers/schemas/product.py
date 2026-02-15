from datetime import datetime
from typing import Optional, Self

from pydantic import Field, model_validator

from infra.web.routers.schemas import CamelModel
from infra.web.routers.schemas.component import ComponentResponseDTO


class ProductCreateDTO(CamelModel):
    name: str
    description: Optional[str] = None


class ProductUpdateDTO(CamelModel):
    name: Optional[str] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def check_update_fields(self) -> Self:
        updates = [
            self.name is not None,
            self.description is not None,
        ]

        if not any(updates):
            raise ValueError("At least one field must be updated")

        return self


class ProductResponseDTO(CamelModel):
    id: int
    name: str
    description: Optional[str] = None
    is_visible: bool
    created_at: datetime
    updated_at: datetime
    components: list[ComponentResponseDTO] = Field(default_factory=list)
