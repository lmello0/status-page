from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from core.domain.status_type import StatusType


class Base(MappedAsDataclass, DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(2000), default=None)

    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        init=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        init=False,
    )

    components: Mapped[list[ComponentModel]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        default_factory=list,
    )


class ComponentModel(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    current_status: Mapped[StatusType] = mapped_column(
        Enum(StatusType, native_enum=False),
        default=StatusType.OPERATIONAL,
        index=True,
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("components.id", ondelete="CASCADE"),
        name="parent_component_id",
        default=None,
        index=True,
    )

    health_url: Mapped[Optional[str]] = mapped_column(String(1024), default=None)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    expected_status_code: Mapped[int] = mapped_column(Integer, default=200)
    max_response_time_ms: Mapped[int] = mapped_column(Integer, default=5000)
    failures_before_outage: Mapped[int] = mapped_column(Integer, default=3)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    product: Mapped[ProductModel] = relationship(back_populates="components", init=False)
    parent: Mapped[Optional[ComponentModel]] = relationship(
        back_populates="subcomponents",
        remote_side="ComponentModel.id",
        default=None,
    )
    subcomponents: Mapped[list[ComponentModel]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        default_factory=list,
    )
