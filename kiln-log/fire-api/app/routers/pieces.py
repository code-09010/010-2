from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Piece
from ..schemas import PieceIn, PieceOut, PiecePatch, PlaceIn
from .firings import get_firing_or_404

router = APIRouter(prefix="/api", tags=["坯件"])


def get_piece_or_404(piece_id: int, db: Session) -> Piece:
    piece = db.get(Piece, piece_id)
    if piece is None:
        raise HTTPException(404, "坯件不存在")
    return piece


@router.post("/firings/{firing_id}/pieces", response_model=PieceOut, status_code=201)
def add_piece(firing_id: int, payload: PieceIn, db: Session = Depends(get_db)):
    firing = get_firing_or_404(firing_id, db)
    if firing.status != "planned":
        raise HTTPException(409, "点火后不能再添坯件")
    piece = Piece(firing_id=firing_id, name=payload.name)
    db.add(piece)
    db.commit()
    db.refresh(piece)
    return piece


@router.patch("/pieces/{piece_id}", response_model=PieceOut)
def patch_piece(piece_id: int, payload: PiecePatch, db: Session = Depends(get_db)):
    piece = get_piece_or_404(piece_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "result" in data and piece.firing.status != "opened":
        raise HTTPException(409, "开窑后才能登记成品结果")
    for key, value in data.items():
        setattr(piece, key, value)
    db.commit()
    db.refresh(piece)
    return piece


@router.post("/pieces/{piece_id}/place", response_model=PieceOut)
def place_piece(piece_id: int, payload: PlaceIn, db: Session = Depends(get_db)):
    piece = get_piece_or_404(piece_id, db)
    firing = piece.firing
    if firing.status != "planned":
        raise HTTPException(409, "点火后窑位就定了，不能再摆")
    if payload.shelf_layer > firing.shelf_layers or payload.slot > firing.slots_per_layer:
        raise HTTPException(422, "窑位超出棚板范围")
    occupant = db.scalar(
        select(Piece).where(
            Piece.firing_id == firing.id,
            Piece.shelf_layer == payload.shelf_layer,
            Piece.slot == payload.slot,
            Piece.id != piece.id,
        )
    )
    if occupant is not None:
        raise HTTPException(409, f"这个窑位已经摆着「{occupant.name}」了")
    piece.shelf_layer = payload.shelf_layer
    piece.slot = payload.slot
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "这个窑位刚被占了，刷新看看")
    db.refresh(piece)
    return piece


@router.post("/pieces/{piece_id}/unplace", response_model=PieceOut)
def unplace_piece(piece_id: int, db: Session = Depends(get_db)):
    piece = get_piece_or_404(piece_id, db)
    if piece.firing.status != "planned":
        raise HTTPException(409, "点火后不能再动窑位")
    piece.shelf_layer = None
    piece.slot = None
    db.commit()
    db.refresh(piece)
    return piece


@router.delete("/pieces/{piece_id}", status_code=204)
def delete_piece(piece_id: int, db: Session = Depends(get_db)):
    piece = get_piece_or_404(piece_id, db)
    if piece.firing.status != "planned":
        raise HTTPException(409, "点火后不能再删坯件")
    db.delete(piece)
    db.commit()
