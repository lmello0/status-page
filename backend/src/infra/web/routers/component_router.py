from fastapi import APIRouter, HTTPException, Query, status

from core.domain.component import Component
from core.domain.page import Page
from core.exceptions.component_already_exists_error import ComponentAlreadyExistsError
from core.exceptions.component_not_found_error import ComponentNotFoundError
from infra.adapter.postgres_component_repository import get_component_repository
from infra.adapter.postgres_log_repository import get_log_repository
from infra.web.routers.schemas.component import (
    ComponentCreateDTO,
    ComponentResponseDTO,
    ComponentUpdateDTO,
)
from infra.web.routers.schemas.page import PageDTO
from use_cases.component.create_component_use_case import CreateComponentUseCase
from use_cases.component.delete_component_use_case import DeleteComponentUseCase
from use_cases.component.get_all_components_by_product_use_case import (
    GetAllComponentsByProductUseCase,
)
from use_cases.component.update_component_use_case import UpdateComponentUseCase

router = APIRouter(prefix="/component", tags=["Component"])


@router.post(
    "",
    response_model=ComponentResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_component(payload: ComponentCreateDTO) -> Component:
    use_case = CreateComponentUseCase(get_component_repository())

    try:
        return await use_case.execute(payload)
    except ComponentAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Component with {e.field}='{e.value}' already exists",
        )


@router.get(
    "",
    response_model=PageDTO[ComponentResponseDTO],
    status_code=status.HTTP_200_OK,
)
async def get_all_components(
    product_id: int = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1),
    summary_days: int = Query(default=100, ge=1, le=365),
) -> Page[Component]:
    use_case = GetAllComponentsByProductUseCase(
        component_repository=get_component_repository(),
        log_repository=get_log_repository(),
    )

    return await use_case.execute(
        product_id=product_id,
        page=page,
        page_size=page_size,
        summary_days=summary_days,
    )


@router.patch(
    "/{component_id}",
    response_model=ComponentResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def update_component(component_id: int, payload: ComponentUpdateDTO) -> Component:
    use_case = UpdateComponentUseCase(get_component_repository())

    try:
        return await use_case.execute(component_id=component_id, component_data=payload)
    except ComponentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    except ComponentAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Component with this {error.field} already exists",
        )


@router.delete(
    "/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_component(component_id: int) -> None:
    use_case = DeleteComponentUseCase(get_component_repository())
    await use_case.execute(component_id)
