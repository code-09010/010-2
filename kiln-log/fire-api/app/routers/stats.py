from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CurveSegment, Firing, Piece
from ..schemas import CrackStat, KilnCrackStat

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


@router.get("/cracks/by-kiln", response_model=list[KilnCrackStat])
def crack_stats_by_kiln(db: Session = Depends(get_db)):
    """按窑炉归组看开裂：哪口窑爱裂、裂多少。没挂档案的老窑次按名字自成一组。"""
    firings = db.scalars(select(Firing).where(Firing.status == "opened")).all()
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

    groups: dict[int | str, KilnCrackStat] = {}
    for f in firings:
        key: int | str = f.kiln_id if f.kiln_id is not None else f"name:{f.kiln_name}"
        g = groups.get(key)
        if g is None:
            g = groups[key] = KilnCrackStat(
                kiln_id=f.kiln_id,
                kiln_name=f.kiln_name,
                opened_count=0,
                total=0,
                good=0,
                cracked=0,
                glaze_crawl=0,
            )
        g.opened_count += 1
        c = counts.get(f.id, {})
        g.total += sum(c.values())
        g.good += c.get("good", 0)
        g.cracked += c.get("cracked", 0)
        g.glaze_crawl += c.get("glaze_crawl", 0)
    return sorted(groups.values(), key=lambda g: (-g.cracked, g.kiln_name))
