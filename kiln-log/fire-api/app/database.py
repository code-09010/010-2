import os
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://kiln:kiln@localhost:5432/kilnlog",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 15, delay: float = 1.0) -> None:
    """建表。compose 里数据库刚起来时连接会失败，重试几次等它就绪。"""
    from . import models  # noqa: F401  确保模型已注册到 metadata

    last_err: Exception | None = None
    for _ in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:  # 数据库还没就绪
            last_err = exc
            time.sleep(delay)
    raise RuntimeError(f"数据库连接失败: {last_err}")
