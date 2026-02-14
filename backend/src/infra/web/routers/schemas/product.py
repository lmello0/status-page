from datetime import datetime
from typing import Optional

from pydantic import Field

from infra.web.routers.schemas import CamelModel
from infra.web.routers.schemas.component import ComponentResponseDTO


class ProductCreateDTO(CamelModel):
    name: str
    description: Optional[str] = None
    is_visible: bool = True


class ProductUpdateDTO(CamelModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_visible: Optional[bool] = None


class ProductResponseDTO(CamelModel):
    id: int
    name: str
    description: Optional[str] = None
    is_visible: bool
    created_at: datetime
    updated_at: datetime
    components: list[ComponentResponseDTO] = Field(default_factory=list)
