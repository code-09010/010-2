from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Atmosphere = Literal["oxidation", "reduction"]
Phase = Literal["heat", "hold", "cool"]
Result = Literal["pending", "good", "cracked", "glaze_crawl"]


# ---- 窑炉档案 ----
class KilnIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    shelf_layers: int = Field(ge=1, le=12)
    slots_per_layer: int = Field(ge=1, le=24)
    note: str = Field(default="", max_length=500)


class KilnPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    shelf_layers: int | None = Field(default=None, ge=1, le=12)
    slots_per_layer: int | None = Field(default=None, ge=1, le=24)
    note: str | None = Field(default=None, max_length=500)


class KilnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    shelf_layers: int
    slots_per_layer: int
    note: str
    created_at: datetime
    firing_count: int = 0  # 挂在这口窑名下的窑次数


# ---- 窑次 ----
class FiringCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kiln_id: int | None = None  # 从档案选窑；不传走老逻辑，自由填 kiln_name
    kiln_name: str = Field(default="主窑", max_length=80)
    atmosphere: Atmosphere = "oxidation"
    shelf_layers: int | None = Field(default=None, ge=1, le=12)  # 空 = 用档案规格
    slots_per_layer: int | None = Field(default=None, ge=1, le=24)
    note: str = Field(default="", max_length=2000)


class FiringPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    kiln_id: int | None = None  # 换挂到另一口窑；名字快照跟着换
    kiln_name: str | None = Field(default=None, max_length=80)
    atmosphere: Atmosphere | None = None
    note: str | None = Field(default=None, max_length=2000)
    shelf_layers: int | None = Field(default=None, ge=1, le=12)
    slots_per_layer: int | None = Field(default=None, ge=1, le=24)


class SegmentIn(BaseModel):
    phase: Phase
    target_temp: int = Field(ge=0, le=1800)
    minutes: int = Field(ge=0, le=100000)


class CurveIn(BaseModel):
    segments: list[SegmentIn]


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phase: str
    target_temp: int
    minutes: int


class PieceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firing_id: int
    name: str
    shelf_layer: int | None
    slot: int | None
    result: str
    note: str


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    temperature: int
    note: str
    recorded_at: datetime


class FiringOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kiln_id: int | None
    kiln_name: str
    atmosphere: str
    status: str
    shelf_layers: int
    slots_per_layer: int
    note: str
    created_at: datetime
    started_at: datetime | None
    opened_at: datetime | None


class FiringSummary(FiringOut):
    piece_total: int = 0  # 这窑一共多少件坯
    placed: int = 0  # 已摆进窑位的
    good: int = 0
    cracked: int = 0
    glaze_crawl: int = 0
    unresulted: int = 0  # 入了窑还没登记结果的


class FiringDetail(FiringOut):
    segments: list[SegmentOut] = []
    pieces: list[PieceOut] = []
    readings: list[ReadingOut] = []


# ---- 坯件 ----
class PieceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PiecePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    result: Result | None = None


class PlaceIn(BaseModel):
    shelf_layer: int = Field(ge=1)
    slot: int = Field(ge=1)


# ---- 看火 ----
class ReadingIn(BaseModel):
    temperature: int = Field(ge=0, le=1800)
    note: str = Field(default="", max_length=200)
    # 补记早些时候的温度时可以带上，默认服务器当前时间
    recorded_at: datetime | None = None


# ---- 统计 ----
class CrackStat(BaseModel):
    firing_id: int
    name: str
    kiln_name: str
    opened_at: datetime | None
    hold_minutes: int | None  # 那窑保温段烧了多少分钟
    total: int  # 出了窑登记了结果的件数
    good: int
    cracked: int
    glaze_crawl: int


class KilnCrackStat(BaseModel):
    """按窑炉归组的开裂汇总。没挂档案的老窑次按名字自成一组，kiln_id 为 None。"""

    kiln_id: int | None
    kiln_name: str
    opened_count: int  # 开了几窑
    total: int
    good: int
    cracked: int
    glaze_crawl: int
