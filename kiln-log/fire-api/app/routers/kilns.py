from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Firing, Kiln
from ..schemas import KilnIn, KilnOut, KilnPatch

router = APIRouter(prefix="/api/kilns", tags=["窑炉档案"])


def get_kiln_or_404(kiln_id: int, db: Session) -> Kiln:
    kiln = db.get(Kiln, kiln_id)
    if kiln is None:
        raise HTTPException(404, "窑炉档案不存在")
    return kiln


@router.get("", response_model=list[KilnOut])
def list_kilns(db: Session = Depends(get_db)):
    kilns = db.scalars(select(Kiln).order_by(Kiln.id)).all()
    counts = dict(
        db.execute(select(Firing.kiln_id, func.count()).group_by(Firing.kiln_id)).all()
    )
    out = []
    for k in kilns:
        ko = KilnOut.model_validate(k)
        ko.firing_count = counts.get(k.id, 0)
        out.append(ko)
    return out


@router.post("", response_model=KilnOut, status_code=201)
def create_kiln(payload: KilnIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(422, "窑名不能为空")
    if db.scalar(select(Kiln.id).where(Kiln.name == name)):
        raise HTTPException(409, f"已经有叫「{name}」的窑了")
    kiln = Kiln(**payload.model_dump(exclude={"name"}), name=name)
    db.add(kiln)
    db.commit()
    db.refresh(kiln)
    return kiln


@router.patch("/{kiln_id}", response_model=KilnOut)
def patch_kiln(kiln_id: int, payload: KilnPatch, db: Session = Depends(get_db)):
    kiln = get_kiln_or_404(kiln_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        name = data["name"].strip()
        if not name:
            raise HTTPException(422, "窑名不能为空")
        clash = db.scalar(select(Kiln.id).where(Kiln.name == name, Kiln.id != kiln_id))
        if clash:
            raise HTTPException(409, f"已经有叫「{name}」的窑了；要并档的话，删掉这口并把窑次并给那口")
        data["name"] = name
    for key, value in data.items():
        setattr(kiln, key, value)
    if "name" in data:
        # 挂在它名下的窑次，名字快照跟着档案改
        db.execute(
            update(Firing).where(Firing.kiln_id == kiln_id).values(kiln_name=data["name"])
        )
    db.commit()
    db.refresh(kiln)
    return kiln


@router.delete("/{kiln_id}", status_code=204)
def delete_kiln(kiln_id: int, reassign_to: int | None = None, db: Session = Depends(get_db)):
    """删档案。名下还有窑次时必须指定 reassign_to，把那些窑并给另一口窑——
    「气窑」「汽窑」这种手滑建重的档案就是这么并掉的。"""
    kiln = get_kiln_or_404(kiln_id, db)
    refs = db.scalars(select(Firing).where(Firing.kiln_id == kiln_id)).all()
    if refs:
        if reassign_to is None:
            raise HTTPException(
                409,
                f"还有 {len(refs)} 窑挂在它名下，带上 reassign_to 把窑次并给别的窑再删",
            )
        target = get_kiln_or_404(reassign_to, db)
        if target.id == kiln_id:
            raise HTTPException(422, "不能并给它自己")
        for f in refs:
            f.kiln_id = target.id
            f.kiln_name = target.name
        db.flush()  # 先把窑次并过去，再删档案，免得 ORM 删档案时把外键置空
    db.delete(kiln)
    db.commit()
