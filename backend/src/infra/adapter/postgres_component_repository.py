from functools import lru_cache
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.domain.component import Component
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.page import Page
from core.exceptions.component_already_exists_error import ComponentAlreadyExistsError
from core.port.component_repository import ComponentRepository
from infra.db.models import ComponentModel
from infra.db.session import get_session_factory


class PostgresComponentRepository(ComponentRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def save(self, component: Component) -> Component:
        async with self._session_factory() as session:
            try:
                model: Optional[ComponentModel] = None
                component_id = component.id

                if component_id is not None and component_id > 0:
                    model = await session.get(ComponentModel, component_id)

                if model is None:
                    model = ComponentModel(
                        product_id=component.product_id,
                        name=component.name,
                        type=component.type,
                        current_status=component.current_status,
                        health_url=component.monitoring_config.health_url,
                        check_interval_seconds=component.monitoring_config.check_interval_seconds,
                        timeout_seconds=component.monitoring_config.timeout_seconds,
                        expected_status_code=component.monitoring_config.expected_status_code,
                        max_response_time_ms=component.monitoring_config.max_response_time_ms,
                        failures_before_outage=component.monitoring_config.failures_before_outage,
                        is_active=component.is_active,
                    )

                    if component_id is not None and component_id > 0:
                        model.id = component_id

                    session.add(model)
                else:
                    model.product_id = component.product_id
                    model.name = component.name
                    model.type = component.type
                    model.current_status = component.current_status
                    model.health_url = component.monitoring_config.health_url
                    model.check_interval_seconds = component.monitoring_config.check_interval_seconds
                    model.timeout_seconds = component.monitoring_config.timeout_seconds
                    model.expected_status_code = component.monitoring_config.expected_status_code
                    model.max_response_time_ms = component.monitoring_config.max_response_time_ms
                    model.failures_before_outage = component.monitoring_config.failures_before_outage
                    model.is_active = component.is_active

                await session.commit()
                await session.refresh(model)

                return self._to_domain(model)

            except IntegrityError as e:
                await session.rollback()

                error_msg = str(e.orig).lower()

                if "name" in error_msg or "components_name_key" in error_msg:
                    raise ComponentAlreadyExistsError("name", component.name)
                elif "health_url" in error_msg or "components_health_url_key" in error_msg:
                    raise ComponentAlreadyExistsError("health_url", component.monitoring_config.health_url)
                else:
                    raise

    async def find_all_by_product_id(self, product_id: int, page: int, page_size: int) -> Page[Component]:
        async with self._session_factory() as session:
            total_elements_statement = select(func.count(ComponentModel.id)).where(
                ComponentModel.product_id == product_id
            )
            total_elements = (await session.execute(total_elements_statement)).scalar_one()

            offset = (page - 1) * page_size
            statement = (
                select(ComponentModel)
                .where(ComponentModel.product_id == product_id)
                .order_by(ComponentModel.id.asc())
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

    async def delete(self, component_id: int) -> bool:
        async with self._session_factory() as session:
            statement = delete(ComponentModel).where(ComponentModel.id == component_id)

            result = await session.execute(statement)
            await session.commit()

            return result.rowcount == 1 # type: ignore

    async def find_all_without_pagination(self) -> list[Component]:
        async with self._session_factory() as session:
            statement = select(ComponentModel).where(ComponentModel.is_active.is_(True))

            models = (await session.execute(statement)).scalars().all()
            content = [self._to_domain(model) for model in models]

            return content

    async def find_by_id(self, component_id: int) -> Optional[Component]:
        async with self._session_factory() as session:
            statement = select(ComponentModel).where(ComponentModel.id == component_id)

            model = (await session.execute(statement)).scalar_one_or_none()

            return self._to_domain(model) if model is not None else None

    def _to_domain(self, model: ComponentModel) -> Component:
        return Component(
            id=model.id,
            product_id=model.product_id,
            name=model.name,
            type=model.type,
            current_status=model.current_status,
            monitoring_config=(
                HealthcheckConfig(
                    health_url=model.health_url,
                    check_interval_seconds=model.check_interval_seconds,
                    timeout_seconds=model.timeout_seconds,
                    expected_status_code=model.expected_status_code,
                    max_response_time_ms=model.max_response_time_ms,
                    failures_before_outage=model.failures_before_outage,
                )
            ),
            is_active=model.is_active,
        )


@lru_cache
def get_component_repository() -> ComponentRepository:
    session_factory = get_session_factory()

    return PostgresComponentRepository(session_factory)
