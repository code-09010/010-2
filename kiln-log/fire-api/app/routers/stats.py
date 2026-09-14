from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CurveSegment, Firing, Piece
from ..schemas import CrackStat

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/cracks", response_model=list[CrackStat])
def crack_stats(
    limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)
):
    """近几窑的开裂情况，摊给老板看，决定下一窑保温要不要加长。"""
    firings = db.scalars(
        select(Firing)
        .where(Firing.status == "opened")
        .order_by(Firing.opened_at.desc().nulls_last(), Firing.id.desc())
        .limit(limit)
    ).all()
    if not firings:
        return []
    ids = [f.id for f in firings]

    counts: dict[int, dict[str, int]] = {}
    rows = db.execute(
        select(Piece.firing_id, Piece.result, func.count())
        .where(Piece.firing_id.in_(ids), Piece.result != "pending")
        .group_by(Piece.firing_id, Piece.result)
    ).all()
    for fid, result, n in rows:
        counts.setdefault(fid, {})[result] = n

    hold = dict(
        db.execute(
            select(CurveSegment.firing_id, CurveSegment.minutes).where(
                CurveSegment.firing_id.in_(ids), CurveSegment.phase == "hold"
            )
        ).all()
    )

    return [
        CrackStat(
            firing_id=f.id,
            name=f.name,
            kiln_name=f.kiln_name,
            opened_at=f.opened_at,
            hold_minutes=hold.get(f.id),
            total=sum(counts.get(f.id, {}).values()),
            good=counts.get(f.id, {}).get("good", 0),
            cracked=counts.get(f.id, {}).get("cracked", 0),
            glaze_crawl=counts.get(f.id, {}).get("glaze_crawl", 0),
        )
        for f in firings
    ]
