from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from core.domain.status_type import StatusType


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        arbitrary_types_allowed=True,
        from_attributes=True,
        populate_by_name=True,
    )


class ProductCreateDTO(CamelModel):
    name: str
    description: Optional[str] = None
    is_visible: bool = True


class ProductUpdateDTO(CamelModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_visible: Optional[bool] = None


class ComponentResponseDTO(CamelModel):
    id: int
    product_id: int
    name: str
    type: str
    current_status: StatusType
    parent_id: Optional[int] = None
    is_active: bool
    subcomponents: list["ComponentResponseDTO"] = Field(default_factory=list)


class ProductResponseDTO(CamelModel):
    id: int
    name: str
    description: Optional[str] = None
    is_visible: bool
    created_at: datetime
    updated_at: datetime
    components: list[ComponentResponseDTO] = Field(default_factory=list)
