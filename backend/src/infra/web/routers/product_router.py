from fastapi import APIRouter, HTTPException, Query, status

from core.domain.page import Page
from core.domain.product import Product
from core.exceptions.product_not_found_error import ProductNotFoundError
from infra.adapter.postgres_product_repository import get_product_repository
from infra.web.routers.schemas.page import PageDTO
from infra.web.routers.schemas.product import ProductCreateDTO, ProductResponseDTO, ProductUpdateDTO
from use_cases.product.create_product_use_case import CreateProductUseCase
from use_cases.product.delete_product_use_case import DeleteProductUseCase
from use_cases.product.get_all_products_use_case import GetAllProductsUseCase
from use_cases.product.get_product_by_id_use_case import GetProductByIdUseCase
from use_cases.product.get_product_by_name_use_case import GetProductByNameUseCase
from use_cases.product.update_product_use_case import UpdateProductUseCase

router = APIRouter(prefix="/product", tags=["Product"])


@router.post(
    "",
    response_model=ProductResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(payload: ProductCreateDTO) -> Product:
    use_case = CreateProductUseCase(get_product_repository())

    return await use_case.execute(payload)


@router.get(
    "",
    response_model=PageDTO[ProductResponseDTO],
    status_code=status.HTTP_200_OK,
)
async def get_all_products(
    is_visible: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1),
) -> Page[Product]:
    use_case = GetAllProductsUseCase(get_product_repository())
    return await use_case.execute(is_visible=is_visible, page=page, page_size=page_size)


@router.get(
    "/{product_id}",
    response_model=ProductResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def get_product_by_id(product_id: int) -> Product:
    use_case = GetProductByIdUseCase(get_product_repository())

    try:
        return await use_case.execute(product_id)
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.get(
    "/name/{product_name}",
    response_model=ProductResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def get_product_by_name(product_name: str) -> Product:
    use_case = GetProductByNameUseCase(get_product_repository())

    try:
        return await use_case.execute(product_name)
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.put(
    "/{product_id}",
    response_model=ProductResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def update_product(product_id: int, payload: ProductUpdateDTO) -> Product:
    use_case = UpdateProductUseCase(get_product_repository())

    try:
        return await use_case.execute(product_id=product_id, product_data=payload)
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_product(product_id: int) -> dict[str, bool]:
    use_case = DeleteProductUseCase(get_product_repository())
    deleted = await use_case.execute(product_id)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return {"deleted": True}
