from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Firing(Base):
    """一窑（窑次）。"""

    __tablename__ = "firings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    kiln_name: Mapped[str] = mapped_column(String(80), default="主窑")
    # oxidation 氧化 / reduction 还原
    atmosphere: Mapped[str] = mapped_column(String(10), default="oxidation")
    # planned 待烧 / firing 烧窑中 / opened 已开窑
    status: Mapped[str] = mapped_column(String(10), default="planned")
    shelf_layers: Mapped[int] = mapped_column(default=4)  # 棚板层数
    slots_per_layer: Mapped[int] = mapped_column(default=6)  # 每层窑位数
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pieces: Mapped[list["Piece"]] = relationship(
        back_populates="firing", cascade="all, delete-orphan", order_by="Piece.id"
    )
    segments: Mapped[list["CurveSegment"]] = relationship(
        back_populates="firing", cascade="all, delete-orphan"
    )
    readings: Mapped[list["Reading"]] = relationship(
        back_populates="firing", cascade="all, delete-orphan", order_by="Reading.recorded_at"
    )


class CurveSegment(Base):
    """烧成曲线的一段：升温 / 保温 / 降温。每窑每段一条。"""

    __tablename__ = "curve_segments"
    __table_args__ = (UniqueConstraint("firing_id", "phase", name="uq_segment_phase"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    firing_id: Mapped[int] = mapped_column(
        ForeignKey("firings.id", ondelete="CASCADE"), index=True
    )
    phase: Mapped[str] = mapped_column(String(10))  # heat 升温 / hold 保温 / cool 降温
    target_temp: Mapped[int]  # 目标温度 ℃
    minutes: Mapped[int]  # 这一段烧多少分钟

    firing: Mapped[Firing] = relationship(back_populates="segments")


class Piece(Base):
    """一件坯。勾进窑位图后记录第几层棚板、第几个窑位。"""

    __tablename__ = "pieces"
    __table_args__ = (
        UniqueConstraint("firing_id", "shelf_layer", "slot", name="uq_piece_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    firing_id: Mapped[int] = mapped_column(
        ForeignKey("firings.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    shelf_layer: Mapped[int | None] = mapped_column(nullable=True)  # 第几层棚板，1 起
    slot: Mapped[int | None] = mapped_column(nullable=True)  # 这层第几个窑位，1 起
    # pending 待登记 / good 成品 / cracked 开裂 / glaze_crawl 釉缩
    result: Mapped[str] = mapped_column(String(12), default="pending")
    note: Mapped[str] = mapped_column(Text, default="")

    firing: Mapped[Firing] = relationship(back_populates="pieces")


class Reading(Base):
    """烧窑中补记的实际看火温度。"""

    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    firing_id: Mapped[int] = mapped_column(
        ForeignKey("firings.id", ondelete="CASCADE"), index=True
    )
    temperature: Mapped[int]
    note: Mapped[str] = mapped_column(String(200), default="")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    firing: Mapped[Firing] = relationship(back_populates="readings")
