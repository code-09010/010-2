"""轻量迁移。项目用 create_all 建表，没有引入 Alembic，这里补上两件 create_all
做不到的事：给已存在的 firings 表补 kiln_id 列，以及按老的 kiln_name 文本
归并出初始窑炉档案、把已有窑次挂上去。

整个流程幂等：重复执行不会重复建档，也不会动已经挂好档案的窑次。
"""

from sqlalchemy import func, inspect, select, text, update
from sqlalchemy.orm import Session

from .database import engine
from .models import Firing, Kiln


def _ensure_kiln_id_column() -> None:
    """老库补 firings.kiln_id 列；新库 create_all 已经带上了，直接跳过。"""
    if "kiln_id" in [c["name"] for c in inspect(engine).get_columns("firings")]:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE firings ADD COLUMN kiln_id INTEGER "
                "REFERENCES kilns(id) ON DELETE SET NULL"
            )
        )


def run_migration(db: Session) -> None:
    _ensure_kiln_id_column()

    # 名字去掉首尾空白后相同的算同一口窑；规格取最近一窑手敲的值
    latest_by_name: dict[str, tuple[int, int]] = {}
    rows = db.execute(
        select(Firing.kiln_name, Firing.shelf_layers, Firing.slots_per_layer).order_by(
            Firing.id
        )
    )
    for name, layers, slots in rows:
        key = name.strip()
        if key:
            latest_by_name[key] = (layers, slots)

    existing = set(db.scalars(select(Kiln.name)))
    for name, (layers, slots) in latest_by_name.items():
        if name not in existing:
            db.add(Kiln(name=name, shelf_layers=layers, slots_per_layer=slots))
    db.flush()

    kiln_id_by_name = dict(db.execute(select(Kiln.name, Kiln.id)).all())
    for name, kiln_id in kiln_id_by_name.items():
        # 顺手把窑次上的名字快照规范成档案名（比如带空格的写法）
        db.execute(
            update(Firing)
            .where(Firing.kiln_id.is_(None), func.trim(Firing.kiln_name) == name)
            .values(kiln_id=kiln_id, kiln_name=name)
        )
    db.commit()
