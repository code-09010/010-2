from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import CurveSegment, Firing, Kiln, Piece
from ..schemas import (
    CurveIn,
    FiringCreate,
    FiringDetail,
    FiringOut,
    FiringPatch,
    FiringSummary,
)

router = APIRouter(prefix="/api/firings", tags=["窑次"])

PHASES = ("heat", "hold", "cool")


def get_firing_or_404(firing_id: int, db: Session) -> Firing:
    firing = db.get(Firing, firing_id)
    if firing is None:
        raise HTTPException(404, "窑次不存在")
    return firing


@router.get("", response_model=list[FiringSummary])
def list_firings(db: Session = Depends(get_db)):
    firings = db.scalars(select(Firing).order_by(Firing.id.desc())).all()
    placed_col = Piece.shelf_layer.is_not(None).label("placed")
    counts: dict[int, list[tuple[str, bool, int]]] = {}
    rows = db.execute(
        select(Piece.firing_id, Piece.result, placed_col, func.count()).group_by(
            Piece.firing_id, Piece.result, placed_col
        )
    ).all()
    for fid, result, placed, n in rows:
        counts.setdefault(fid, []).append((result, placed, n))
    out = []
    for f in firings:
        s = FiringSummary.model_validate(f)
        for result, placed, n in counts.get(f.id, []):
            s.piece_total += n
            if placed:
                s.placed += n
                if result == "pending":
                    s.unresulted += n
            if result == "good":
                s.good += n
            elif result == "cracked":
                s.cracked += n
            elif result == "glaze_crawl":
                s.glaze_crawl += n
        out.append(s)
    return out


@router.post("", response_model=FiringOut, status_code=201)
def create_firing(payload: FiringCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    kiln = None
    if data["kiln_id"] is not None:
        kiln = db.get(Kiln, data["kiln_id"])
        if kiln is None:
            raise HTTPException(404, "窑炉档案不存在")
        data["kiln_name"] = kiln.name  # 快照档案名，不再手敲
    # 层数窑位没显式填就用档案规格；填了就是这一窑的临时覆盖
    data["shelf_layers"] = data["shelf_layers"] or (kiln.shelf_layers if kiln else 4)
    data["slots_per_layer"] = data["slots_per_layer"] or (
        kiln.slots_per_layer if kiln else 6
    )
    firing = Firing(**data)
    db.add(firing)
    db.commit()
    db.refresh(firing)
    return firing


@router.get("/{firing_id}", response_model=FiringDetail)
def firing_detail(firing_id: int, db: Session = Depends(get_db)):
    firing = db.scalar(
        select(Firing)
        .where(Firing.id == firing_id)
        .options(
            selectinload(Firing.pieces),
            selectinload(Firing.readings),
            selectinload(Firing.segments),
        )
    )
    if firing is None:
        raise HTTPException(404, "窑次不存在")
    detail = FiringDetail.model_validate(firing)
    order = {p: i for i, p in enumerate(PHASES)}
    detail.segments.sort(key=lambda s: order.get(s.phase, 99))
    return detail


@router.patch("/{firing_id}", response_model=FiringOut)
def patch_firing(firing_id: int, payload: FiringPatch, db: Session = Depends(get_db)):
    firing = get_firing_or_404(firing_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "kiln_id" in data:
        kiln_id = data.pop("kiln_id")
        if kiln_id is None:
            firing.kiln_id = None  # 只摘档案，名字快照留着
        else:
            kiln = db.get(Kiln, kiln_id)
            if kiln is None:
                raise HTTPException(404, "窑炉档案不存在")
            firing.kiln_id = kiln.id
            data["kiln_name"] = kiln.name  # 换了档案，名字快照跟着换
    new_layers = data.get("shelf_layers", firing.shelf_layers)
    new_slots = data.get("slots_per_layer", firing.slots_per_layer)
    if (new_layers, new_slots) != (firing.shelf_layers, firing.slots_per_layer):
        if firing.status != "planned":
            raise HTTPException(409, "点火后不能再改棚板层数和窑位数")
        overflow = db.scalar(
            select(func.count())
            .select_from(Piece)
            .where(
                Piece.firing_id == firing_id,
                (Piece.shelf_layer > new_layers) | (Piece.slot > new_slots),
            )
        )
        if overflow:
            raise HTTPException(409, "有坯件超出新的窑位范围，先把它撤下来")
    for key, value in data.items():
        setattr(firing, key, value)
    db.commit()
    db.refresh(firing)
    return firing


@router.delete("/{firing_id}", status_code=204)
def delete_firing(firing_id: int, db: Session = Depends(get_db)):
    firing = get_firing_or_404(firing_id, db)
    db.delete(firing)
    db.commit()


@router.post("/{firing_id}/start", response_model=FiringOut)
def start_firing(firing_id: int, db: Session = Depends(get_db)):
    firing = get_firing_or_404(firing_id, db)
    if firing.status != "planned":
        raise HTTPException(409, "只有待烧的窑次才能点火")
    firing.status = "firing"
    firing.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(firing)
    return firing


@router.post("/{firing_id}/open", response_model=FiringOut)
def open_firing(firing_id: int, db: Session = Depends(get_db)):
    firing = get_firing_or_404(firing_id, db)
    if firing.status != "firing":
        raise HTTPException(409, "只有烧窑中的窑次才能开窑")
    firing.status = "opened"
    firing.opened_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(firing)
    return firing


@router.put("/{firing_id}/curve", response_model=FiringDetail)
def put_curve(firing_id: int, payload: CurveIn, db: Session = Depends(get_db)):
    """整段替换烧成曲线，必须正好升温、保温、降温三段。"""
    firing = get_firing_or_404(firing_id, db)
    if firing.status == "opened":
        raise HTTPException(409, "已开窑，曲线留档不能再改")
    phases = [s.phase for s in payload.segments]
    if sorted(phases) != sorted(PHASES):
        raise HTTPException(422, "曲线必须正好包含升温、保温、降温三段")
    firing.segments.clear()
    db.flush()  # 先删掉旧段，再放新段，避免 (firing_id, phase) 唯一约束冲突
    for seg in payload.segments:
        firing.segments.append(CurveSegment(**seg.model_dump()))
    db.commit()
    return firing_detail(firing_id, db)
