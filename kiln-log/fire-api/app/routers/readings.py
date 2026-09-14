from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Reading
from ..schemas import ReadingIn, ReadingOut
from .firings import get_firing_or_404

router = APIRouter(prefix="/api", tags=["看火"])


@router.post(
    "/firings/{firing_id}/readings", response_model=ReadingOut, status_code=201
)
def add_reading(firing_id: int, payload: ReadingIn, db: Session = Depends(get_db)):
    firing = get_firing_or_404(firing_id, db)
    if firing.status != "firing":
        raise HTTPException(409, "只有烧窑中才能补看火温度")
    data = payload.model_dump()
    if data.get("recorded_at") is None:
        data.pop("recorded_at")  # 用服务器当前时间
    reading = Reading(firing_id=firing_id, **data)
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.delete("/readings/{reading_id}", status_code=204)
def delete_reading(reading_id: int, db: Session = Depends(get_db)):
    reading = db.get(Reading, reading_id)
    if reading is None:
        raise HTTPException(404, "这条看火记录不存在")
    db.delete(reading)
    db.commit()
