from collections import defaultdict
from functools import lru_cache
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from core.domain.component import Component
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.page import Page
from core.domain.product import Product
from core.port.product_repository import ProductRepository
from infra.db.models import ComponentModel, ProductModel
from infra.db.session import get_session_factory


class PostgresProductRepository(ProductRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def save(self, product: Product) -> Product:
        async with self._session_factory() as session:
            model: Optional[ProductModel] = None

            if product.id > 0:
                model = await session.get(ProductModel, product.id)

            if model is None:
                model = ProductModel(
                    name=product.name,
                    description=product.description,
                    is_visible=product.is_visible,
                )

                if product.id > 0:
                    model.id = product.id

                session.add(model)
            else:
                model.name = product.name
                model.description = product.description
                model.is_visible = product.is_visible

            await session.commit()
            await session.refresh(model)

            return Product(
                id=model.id,
                name=model.name,
                description=model.description,
                is_visible=model.is_visible,
                created_at=model.created_at,
                updated_at=model.updated_at,
                components=product.components,
            )

    async def find_by_id(self, product_id: int) -> Optional[Product]:
        async with self._session_factory() as session:
            statement = (
                select(ProductModel).options(selectinload(ProductModel.components)).where(ProductModel.id == product_id)
            )
            model = (await session.execute(statement)).scalar_one_or_none()

            if model is None:
                return None

            return self._to_domain(model)

    async def find_by_name(self, name: str) -> Optional[Product]:
        async with self._session_factory() as session:
            statement = (
                select(ProductModel).options(selectinload(ProductModel.components)).where(ProductModel.name == name)
            )
            model = (await session.execute(statement)).scalar_one_or_none()

            if model is None:
                return None

            return self._to_domain(model)

    async def find_all(self, is_visible: bool, page: int, page_size: int) -> Page[Product]:
        async with self._session_factory() as session:
            total_elements_statement = select(func.count(ProductModel.id)).where(
                ProductModel.is_visible.is_(is_visible)
            )
            total_elements = (await session.execute(total_elements_statement)).scalar_one()

            offset = (page - 1) * page_size
            statement = (
                select(ProductModel)
                .options(selectinload(ProductModel.components))
                .where(ProductModel.is_visible.is_(is_visible))
                .order_by(ProductModel.id.asc())
                .offset(offset)
                .limit(page_size)
            )
            models = (await session.execute(statement)).scalars().all()
            content = [self._to_domain(model) for model in models]

            total_pages = (total_elements + page_size - 1) // page_size if total_elements > 0 else 0

            return Page(
                page_size=page_size,
                page_count=len(content),
                total_elements=total_elements,
                total_pages=total_pages,
                content=content,
            )

    async def delete(self, product_id: int) -> bool:
        async with self._session_factory() as session:
            statement = delete(ProductModel).where(ProductModel.id == product_id)

            await session.execute(statement)
            await session.commit()

            result = await session.execute(select(ProductModel).where(ProductModel.id == product_id))

            return result.scalar_one_or_none() is None

    def _to_domain(self, model: ProductModel) -> Product:
        return Product(
            id=model.id,
            name=model.name,
            description=model.description,
            is_visible=model.is_visible,
            created_at=model.created_at,
            updated_at=model.updated_at,
            components=self._map_components(model.components),
        )

    def _map_components(self, models: list[ComponentModel]) -> list[Component]:
        if not models:
            return []

        children_by_parent: dict[Optional[int], list[ComponentModel]] = defaultdict(list)
        for model in models:
            children_by_parent[model.parent_id].append(model)

        for siblings in children_by_parent.values():
            siblings.sort(key=lambda item: item.id)

        def build_tree(parent_id: Optional[int]) -> list[Component]:
            return [
                Component(
                    id=model.id,
                    product_id=model.product_id,
                    name=model.name,
                    type=model.type,
                    current_status=model.current_status,
                    parent_id=model.parent_id,
                    subcomponents=build_tree(model.id),
                    monitoring_config=(
                        HealthcheckConfig(
                            health_url=model.health_url,
                            check_interval_seconds=model.check_interval_seconds,
                            timeout_seconds=model.timeout_seconds,
                            expected_status_code=model.expected_status_code,
                            max_response_time_ms=model.max_response_time_ms,
                            failures_before_outage=model.failures_before_outage,
                        )
                        if model.health_url
                        else None
                    ),
                    is_active=model.is_active,
                )
                for model in children_by_parent[parent_id]
            ]

        return build_tree(None)


@lru_cache
def get_product_repository() -> ProductRepository:
    session_factory = get_session_factory()

    return PostgresProductRepository(session_factory)
